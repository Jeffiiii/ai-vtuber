"""Merge a LoRA adapter into the base HF model.

Use this only after the adapter passes A/B evaluation.

Example:

python scripts/posttrain/merge_lora_for_export.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter output/lora-elysia-3b-v1 \
  --out output/merged-elysia-3b-v1 \
  --torch-dtype bfloat16 \
  --device-map auto
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--torch-dtype", choices=["float16", "bfloat16", "float32"], default="bfloat16")
    ap.add_argument("--device-map", default="auto")
    ap.add_argument("--max-shard-size", default="4GB")
    return ap.parse_args()


def dtype_from_name(name: str):
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[name]


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    dtype = dtype_from_name(args.torch_dtype)

    print("Loading tokenizer...")
    tok = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    print("Loading base model in full precision dtype for clean merge...")
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=dtype,
        device_map=args.device_map,
        trust_remote_code=True,
    )

    print("Loading adapter...")
    model = PeftModel.from_pretrained(base, args.adapter)

    print("Merging adapter into base weights...")
    merged = model.merge_and_unload()
    merged.eval()

    print(f"Saving merged model to {out} ...")
    merged.save_pretrained(out, safe_serialization=True, max_shard_size=args.max_shard_size)
    tok.save_pretrained(out)

    manifest = {
        "base_model": args.base_model,
        "adapter": args.adapter,
        "merged_out": str(out),
        "torch_dtype": args.torch_dtype,
        "note": "Merged Hugging Face model. Test it before GGUF/Ollama conversion.",
    }
    (out / "merge_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Done:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
