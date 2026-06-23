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
    p.add_argument("--max-seq-len", type=int, default=1024)
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
                              DataCollatorForLanguageModeling, Trainer, TrainingArguments)

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

    def to_text(example):
        # Render the chat turns into the model's training format. enable_thinking=False
        # keeps Qwen3 from injecting a <think> phase (we want snappy replies).
        kwargs = dict(tokenize=False, add_generation_prompt=False)
        try:
            text = tok.apply_chat_template(example["messages"], enable_thinking=False, **kwargs)
        except TypeError:
            text = tok.apply_chat_template(example["messages"], **kwargs)
        return {"text": text}

    ds = load_dataset("json", data_files=args.data, split="train")
    if args.smoke:
        ds = ds.select(range(min(8, len(ds))))
    ds = ds.map(to_text, remove_columns=ds.column_names)

    def tokenize(example):
        return tok(example["text"], truncation=True, max_length=args.max_seq_len)

    ds = ds.map(tokenize, remove_columns=["text"])
    print(f"Training examples: {len(ds)}")

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

    collator = DataCollatorForLanguageModeling(tok, mlm=False)

    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=1 if args.smoke else args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=1 if args.smoke else args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=2 if args.smoke else 5,
        save_strategy="no" if args.smoke else "epoch",
        bf16=bf16_ok,
        fp16=not bf16_ok,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        report_to="none",
    )

    trainer = Trainer(model=model, args=targs, train_dataset=ds, data_collator=collator)
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
