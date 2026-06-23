"""Heavy A/B evaluation: base model vs LoRA adapter.

Loads and evaluates the base model first, releases it, then loads the LoRA-adapted
model. This is friendlier to 8 GB GPUs than loading both at once.

Example:

python scripts/posttrain/heavy_ab_eval_lora.py \
  --character elysia \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter output/lora-elysia-3b-v1 \
  --eval-file eval/elysia_eval.jsonl \
  --out-dir posttrain_results/elysia_3b_ab \
  --load-4bit \
  --temperature 0.2 \
  --max-new-tokens 220
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from eval_utils import (
    basic_checks,
    clear_gpu_memory,
    generate_one,
    load_system_prompt,
    model_memory_note,
    read_jsonl,
    row_passes,
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
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--system-prompt")
    ap.add_argument("--system-file")
    return ap.parse_args()


def load_base(base_model: str, load_4bit: bool):
    quant = None
    if load_4bit:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    tok = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        quantization_config=quant,
        trust_remote_code=True,
    )
    model.eval()
    return model, tok


def run_eval(model, tok, tests, system, args, label):
    rows = []
    total = len(tests) * args.repeats
    idx = 0

    for rep in range(args.repeats):
        for t in tests:
            idx += 1
            prompt = t["prompt"]
            print(f"[{label} {idx}/{total}] {t.get('id', idx)}: {prompt[:80]!r}")
            start = time.perf_counter()
            try:
                response = generate_one(
                    model, tok, system, prompt,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
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
                "repeat": rep + 1,
                "model_label": label,
                "response": response,
                "latency_s": latency,
                "checks": checks,
            }
            rows.append(row)
            print(f"  {latency}s | pass={row_passes(row, args.character)} | {response[:120]!r}")
    return rows


def write_comparison_csv(path: Path, base_rows, adapter_rows, character: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    by_key_base = {(r.get("id"), r.get("repeat", 1)): r for r in base_rows}
    by_key_adapt = {(r.get("id"), r.get("repeat", 1)): r for r in adapter_rows}

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "id", "repeat", "category", "language", "prompt",
            "base_pass", "adapter_pass", "base_chars", "adapter_chars",
            "base_response", "adapter_response"
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key in sorted(by_key_base.keys()):
            b = by_key_base[key]
            a = by_key_adapt.get(key)
            if not a:
                continue
            w.writerow({
                "id": key[0],
                "repeat": key[1],
                "category": b.get("category"),
                "language": b.get("language"),
                "prompt": b.get("prompt"),
                "base_pass": row_passes(b, character),
                "adapter_pass": row_passes(a, character),
                "base_chars": b["checks"].get("char_count"),
                "adapter_chars": a["checks"].get("char_count"),
                "base_response": b.get("response"),
                "adapter_response": a.get("response"),
            })


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tests = read_jsonl(args.eval_file)
    if args.limit:
        tests = tests[: args.limit]
    system = load_system_prompt(args.character, args.system_prompt, args.system_file)

    print("=== BASE MODEL EVAL ===")
    base, tok = load_base(args.base_model, args.load_4bit)
    base_rows = run_eval(base, tok, tests, system, args, "base")
    base_summary = summarize_results(base_rows, args.character)
    base_summary["gpu_memory_after_base"] = model_memory_note()
    write_jsonl(out_dir / "base_results.jsonl", base_rows)
    write_json(out_dir / "base_summary.json", base_summary)

    del base
    clear_gpu_memory()

    print("\n=== ADAPTER MODEL EVAL ===")
    base2, tok2 = load_base(args.base_model, args.load_4bit)
    model = PeftModel.from_pretrained(base2, args.adapter)
    model.eval()
    adapter_rows = run_eval(model, tok2, tests, system, args, "adapter")
    adapter_summary = summarize_results(adapter_rows, args.character)
    adapter_summary["gpu_memory_after_adapter"] = model_memory_note()
    write_jsonl(out_dir / "adapter_results.jsonl", adapter_rows)
    write_json(out_dir / "adapter_summary.json", adapter_summary)

    write_comparison_csv(out_dir / "comparison.csv", base_rows, adapter_rows, args.character)

    combined = {
        "character": args.character,
        "base_model": args.base_model,
        "adapter": args.adapter,
        "base": {k: base_summary[k] for k in ["total", "passed", "failed", "pass_rate", "avg_latency_s"]},
        "adapter": {k: adapter_summary[k] for k in ["total", "passed", "failed", "pass_rate", "avg_latency_s"]},
        "delta_pass_rate": round(adapter_summary["pass_rate"] - base_summary["pass_rate"], 4),
    }
    write_json(out_dir / "summary.json", combined)

    print("\n=== SUMMARY ===")
    print(json.dumps(combined, ensure_ascii=False, indent=2))
    print("Wrote:", out_dir)

    del model
    del base2
    clear_gpu_memory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
