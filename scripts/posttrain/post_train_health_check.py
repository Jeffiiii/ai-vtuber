"""Post-training health check for a LoRA adapter.

Example:

python scripts/posttrain/post_train_health_check.py \
  --character elysia \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter output/lora-elysia-3b-v1 \
  --eval-file eval/elysia_eval.jsonl \
  --out posttrain_results/elysia_health.jsonl \
  --limit 8 \
  --load-4bit
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from eval_utils import (
    basic_checks,
    clear_gpu_memory,
    generate_one,
    load_system_prompt,
    model_memory_note,
    read_jsonl,
    summarize_results,
    write_json,
    write_jsonl,
)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--character", required=True, choices=["elysia", "cyrene"])
    ap.add_argument("--base-model", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--eval-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary-out")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--system-prompt")
    ap.add_argument("--system-file")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    adapter = Path(args.adapter)

    required = ["adapter_config.json"]
    missing = [name for name in required if not (adapter / name).exists()]
    if not any((adapter / name).exists() for name in ["adapter_model.safetensors", "adapter_model.bin"]):
        missing.append("adapter_model.safetensors or adapter_model.bin")
    if missing:
        raise SystemExit(f"Missing adapter files in {adapter}: {missing}")

    print("Loading adapter config...")
    peft_cfg = PeftConfig.from_pretrained(str(adapter))
    print(json.dumps({
        "peft_type": str(peft_cfg.peft_type),
        "base_model_name_or_path": peft_cfg.base_model_name_or_path,
        "target_modules": sorted(list(peft_cfg.target_modules or [])),
    }, indent=2))

    print("Loading tokenizer...")
    tok = AutoTokenizer.from_pretrained(args.adapter, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = None
    if args.load_4bit:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    print("Loading base model...")
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        quantization_config=quant,
        trust_remote_code=True,
    )

    print("Attaching LoRA adapter...")
    model = PeftModel.from_pretrained(base, str(adapter))
    model.eval()

    tests = read_jsonl(args.eval_file)
    if args.limit:
        tests = tests[: args.limit]
    system = load_system_prompt(args.character, args.system_prompt, args.system_file)

    rows = []
    for i, t in enumerate(tests, start=1):
        prompt = t["prompt"]
        print(f"[{i}/{len(tests)}] {t.get('id', i)}: {prompt[:80]!r}")
        start = time.perf_counter()
        try:
            response = generate_one(
                model, tok, system, prompt,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            err = None
        except Exception as e:
            response = ""
            err = repr(e)
        latency = round(time.perf_counter() - start, 3)
        checks = basic_checks(response, t.get("expected_language") or t.get("language"), args.character)
        checks["error"] = err

        row = {
            **t,
            "response": response,
            "latency_s": latency,
            "checks": checks,
        }
        rows.append(row)
        print(f"  {latency}s | lang_ok={checks['language_ok']} | empty={checks['empty']} | {response[:120]!r}")

    write_jsonl(args.out, rows)
    summary = summarize_results(rows, args.character)
    summary["gpu_memory"] = model_memory_note()
    summary["adapter"] = str(adapter)
    summary["base_model"] = args.base_model

    summary_out = args.summary_out or str(Path(args.out).with_suffix(".summary.json"))
    write_json(summary_out, summary)

    print("\nSummary:")
    print(json.dumps({k: summary[k] for k in ["total", "passed", "failed", "pass_rate", "avg_latency_s"]}, indent=2))
    print("Wrote:", args.out)
    print("Wrote:", summary_out)

    del model
    del base
    clear_gpu_memory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
