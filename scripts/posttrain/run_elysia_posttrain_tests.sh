#!/usr/bin/env bash
set -euo pipefail

BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-3B-Instruct}"
ADAPTER="${ADAPTER:-output/lora-elysia-3b-v1}"
EVAL_FILE="${EVAL_FILE:-eval/elysia_eval.jsonl}"
OUT_DIR="${OUT_DIR:-posttrain_results/elysia_3b}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-220}"

mkdir -p "$OUT_DIR"

python scripts/posttrain/dataset_adapter_sanity.py \
  --train-jsonl data/elysia_train.jsonl \
  --eval-jsonl "$EVAL_FILE" \
  --adapter "$ADAPTER"

python scripts/posttrain/post_train_health_check.py \
  --character elysia \
  --base-model "$BASE_MODEL" \
  --adapter "$ADAPTER" \
  --eval-file "$EVAL_FILE" \
  --out "$OUT_DIR/health.jsonl" \
  --limit 8 \
  --load-4bit \
  --max-new-tokens "$MAX_NEW_TOKENS"

python scripts/posttrain/heavy_ab_eval_lora.py \
  --character elysia \
  --base-model "$BASE_MODEL" \
  --adapter "$ADAPTER" \
  --eval-file "$EVAL_FILE" \
  --out-dir "$OUT_DIR/ab" \
  --load-4bit \
  --temperature 0.2 \
  --max-new-tokens "$MAX_NEW_TOKENS"

echo "A/B testing complete. Inspect: $OUT_DIR/ab/comparison.csv"
echo "Only merge if the adapter results are better than the base results."
