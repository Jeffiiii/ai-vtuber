"""Evaluate a merged Hugging Face model after LoRA merge.

Example:

python scripts/posttrain/test_merged_hf_model.py \
  --character elysia \
  --model output/merged-elysia-3b-v1 \
  --eval-file eval/elysia_eval.jsonl \
  --out-dir posttrain_results/elysia_merged \
  --temperature 0.2 \
  --max-new-tokens 220
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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
    ap.add_argument("--model", required=True)
    ap.add_argument("--eval-file", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--torch-dtype", choices=["float16", "bfloat16", "float32"], default="bfloat16")
    ap.add_argument("--system-prompt")
    ap.add_argument("--system-file")
    return ap.parse_args()


def dtype_from_name(name):
    return {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}[name]


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype_from_name(args.torch_dtype),
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    tests = read_jsonl(args.eval_file)
    if args.limit:
        tests = tests[: args.limit]
    system = load_system_prompt(args.character, args.system_prompt, args.system_file)

    rows = []
    for i, t in enumerate(tests, start=1):
        prompt = t["prompt"]
        print(f"[merged {i}/{len(tests)}] {t.get('id', i)}: {prompt[:80]!r}")
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
        row = {**t, "model_label": "merged", "response": response, "latency_s": latency, "checks": checks}
        rows.append(row)
        print(f"  {latency}s | lang_ok={checks['language_ok']} | empty={checks['empty']} | {response[:120]!r}")

    write_jsonl(out_dir / "merged_results.jsonl", rows)
    summary = summarize_results(rows, args.character)
    summary["gpu_memory"] = model_memory_note()
    summary["model"] = args.model
    write_json(out_dir / "merged_summary.json", summary)

    print("\nSummary:")
    print(json.dumps({k: summary[k] for k in ["total", "passed", "failed", "pass_rate", "avg_latency_s"]}, indent=2))
    print("Wrote:", out_dir)

    del model
    clear_gpu_memory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
