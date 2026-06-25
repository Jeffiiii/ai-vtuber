"""QLoRA supervised fine-tuning for the ai-vtuber characters (Qwen3, 8GB-friendly).

Trains a LoRA adapter on a chat JSONL file where every line is:
    {"messages": [{"role":"system",...},{"role":"user",...},{"role":"assistant",...}]}

Designed to fit an RTX 4060 (8GB) via 4-bit (QLoRA). Run inside WSL2.

Examples
--------
  # 1) wiring check on a handful of examples (fast, proves the pipeline works)
  python train/sft_lora.py --data data/elysia_train.jsonl --smoke

  # 2) real run (a few hours on a 4060)
  python train/sft_lora.py --data data/elysia_train.jsonl \
      --model Qwen/Qwen3-4B --out output/lora-elysia --epochs 3

Output: a LoRA adapter saved to --out (snap it onto the base model at inference,
or merge it with scripts/posttrain/merge_lora_for_export.py).
"""

from __future__ import annotations

import argparse
import os


def parse_args():
    p = argparse.ArgumentParser(description="QLoRA SFT for ai-vtuber characters")
    p.add_argument("--data", required=True, help="Path to chat JSONL (messages format)")
    p.add_argument("--model", default="Qwen/Qwen3-4B",
                   help="Base model (HF id). Qwen3-4B fits 8GB comfortably; Qwen3-8B also works.")
    p.add_argument("--out", default="output/lora-elysia", help="Where to save the adapter")
    p.add_argument("--epochs", type=float, default=3.0)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--max-seq-len", type=int, default=2048,
                   help="Raised from 1024 so long replies aren't truncated (the tail of the "
                        "assistant turn is the training target).")
    p.add_argument("--val-frac", type=float, default=0.1,
                   help="Held-out validation fraction (for eval_loss / best-model selection).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch", type=int, default=1, help="Per-device batch size (keep 1 on 8GB)")
    p.add_argument("--grad-accum", type=int, default=16, help="Gradient accumulation steps")
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=16)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--smoke", action="store_true",
                   help="Tiny run: 8 examples, 1 epoch — just to confirm the toolchain works.")
    return p.parse_args()


def main():
    args = parse_args()

    # Heavy imports inside main so --help is instant and import errors are clear.
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                              DataCollatorForSeq2Seq, Trainer, TrainingArguments, set_seed)

    set_seed(args.seed)   # reproducible split + init

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA GPU not visible to PyTorch. Inside WSL2, check `nvidia-smi` works and that "
            "you installed the CUDA build of torch (the cu124/cu126 index)."
        )
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    # bf16 is supported on Ada (RTX 40-series); fall back to fp16 otherwise.
    bf16_ok = torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if bf16_ok else torch.float16

    # ---- tokenizer ----
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def _template(messages, add_generation_prompt):
        kwargs = dict(tokenize=False, add_generation_prompt=add_generation_prompt)
        try:
            return tok.apply_chat_template(messages, enable_thinking=False, **kwargs)
        except TypeError:
            return tok.apply_chat_template(messages, **kwargs)

    def encode(example):
        # Completion-only loss: render the full chat AND the prompt-only prefix, then
        # mask every prompt/template token to -100 so loss is computed ONLY over her
        # assistant reply (the voice we're actually training), not the repeated template.
        msgs = example["messages"]
        full = _template(msgs, add_generation_prompt=False)
        prompt = _template(msgs[:-1], add_generation_prompt=True)
        full_ids = tok(full, truncation=True, max_length=args.max_seq_len)["input_ids"]
        prompt_ids = tok(prompt, truncation=True, max_length=args.max_seq_len)["input_ids"]
        labels = list(full_ids)
        for i in range(min(len(prompt_ids), len(labels))):
            labels[i] = -100
        return {"input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": labels}

    raw = load_dataset("json", data_files=args.data, split="train")
    if args.smoke:
        raw = raw.select(range(min(8, len(raw))))
    encoded = raw.map(encode, remove_columns=raw.column_names)

    # Held-out validation set so we can watch eval_loss and keep the best epoch,
    # instead of blindly saving the final (possibly overfit) one.
    eval_ds = None
    if not args.smoke and len(encoded) >= 20 and args.val_frac > 0:
        split = encoded.train_test_split(test_size=args.val_frac, seed=args.seed)
        ds, eval_ds = split["train"], split["test"]
    else:
        ds = encoded
    print(f"Training examples: {len(ds)}" + (f" | validation: {len(eval_ds)}" if eval_ds else ""))

    # ---- 4-bit base model (QLoRA) ----
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    # Put the WHOLE model on GPU 0. "auto" can over-cautiously offload layers to CPU
    # on an 8GB laptop GPU, which 4-bit can't do — Qwen3-4B in 4-bit is ~3GB and fits.
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=bnb, device_map={"": 0},
        torch_dtype=compute_dtype, trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    # pads input_ids/attention_mask AND labels (with -100), preserving the masking.
    collator = DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100)

    do_eval = eval_ds is not None
    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=1 if args.smoke else args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=1 if args.smoke else args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=2 if args.smoke else 5,
        save_strategy="no" if args.smoke else "epoch",
        eval_strategy="epoch" if do_eval else "no",
        load_best_model_at_end=do_eval,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=bf16_ok,
        fp16=not bf16_ok,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        seed=args.seed,
        report_to="none",
    )

    trainer = Trainer(model=model, args=targs, train_dataset=ds,
                      eval_dataset=eval_ds, data_collator=collator)
    trainer.train()

    if args.smoke:
        print("\nSMOKE OK — pipeline runs end to end. Now do a real run (drop --smoke).")
        return

    os.makedirs(args.out, exist_ok=True)
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"\nDone. LoRA adapter saved to: {args.out}")
    print("Next: evaluate it (scripts/posttrain/post_train_health_check.py), then merge for serving.")


if __name__ == "__main__":
    main()
