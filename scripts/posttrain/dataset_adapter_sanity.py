"""Extra sanity checks before/after training.

Checks:
- Training JSONL can be parsed.
- Rows have messages=[system,user,assistant].
- Eval JSONL can be parsed.
- Adapter folder exists and has required files.

Example:
python scripts/posttrain/dataset_adapter_sanity.py \
  --train-jsonl data/elysia_train.jsonl \
  --eval-jsonl eval/elysia_eval.jsonl \
  --adapter output/lora-elysia-3b-v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise SystemExit(f"{path}:{i} invalid JSON: {e}")
    return rows


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-jsonl", required=True)
    ap.add_argument("--eval-jsonl", required=True)
    ap.add_argument("--adapter")
    return ap.parse_args()


def main():
    args = parse_args()

    train = parse_jsonl(args.train_jsonl)
    eval_rows = parse_jsonl(args.eval_jsonl)

    problems = []
    for i, row in enumerate(train, 1):
        msgs = row.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 3:
            problems.append(f"train row {i}: expected 3 messages")
            continue
        roles = [m.get("role") for m in msgs]
        if roles != ["system", "user", "assistant"]:
            problems.append(f"train row {i}: wrong roles {roles}")
        if not all((m.get("content") or "").strip() for m in msgs):
            problems.append(f"train row {i}: empty content")

    for i, row in enumerate(eval_rows, 1):
        if not row.get("prompt"):
            problems.append(f"eval row {i}: empty prompt")
        if not (row.get("language") or row.get("expected_language")):
            problems.append(f"eval row {i}: no language")

    if args.adapter:
        adapter = Path(args.adapter)
        if not adapter.exists():
            problems.append(f"adapter missing: {adapter}")
        if not (adapter / "adapter_config.json").exists():
            problems.append(f"adapter_config.json missing in {adapter}")
        if not ((adapter / "adapter_model.safetensors").exists() or (adapter / "adapter_model.bin").exists()):
            problems.append(f"adapter weights missing in {adapter}")

    print(json.dumps({
        "train_rows": len(train),
        "eval_rows": len(eval_rows),
        "adapter": args.adapter,
        "problems": problems,
        "ok": not problems,
    }, ensure_ascii=False, indent=2))

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
