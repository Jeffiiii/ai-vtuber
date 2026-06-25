#!/usr/bin/env bash
# Phase 0 — freeze the voice: smoke -> train (v1 data only) -> merge.
# Eval (health check) and serving stay MANUAL on purpose (see PHASE0_VOICE_RETRAIN.md).
#
# Run inside WSL2 with the training venv active:
#   source ~/ai-vtuber/.venv-train/bin/activate
#   cd /mnt/c/Users/Leo12/Documents/ai-vtuber
#   bash run_phase0_voice.sh
#
# Override any path via env, e.g.:  BASE=/home/leo12/models/Qwen3-4B EPOCHS=3 bash run_phase0_voice.sh
set -euo pipefail

# --- config (override via environment) ---------------------------------------
BASE="${BASE:-/home/leo12/models/Qwen3-4B}"     # local base model (from your v2 merge_manifest)
DATA="${DATA:-data/elysia_train.jsonl}"         # v1 = voice only (DO NOT use v2 / v2_1)
ADAPTER_OUT="${ADAPTER_OUT:-output/lora-elysia-v1voice}"
MERGED_OUT="${MERGED_OUT:-output/elysia-merged-v1voice}"
EPOCHS="${EPOCHS:-3}"
MERGE_DEVICE_MAP="${MERGE_DEVICE_MAP:-auto}"     # set to 'cpu' if the merge OOMs on 8GB

export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

echo "================ Phase-0 voice retrain ================"
echo "base:    $BASE"
echo "data:    $DATA  (must be the v1 voice file)"
echo "adapter: $ADAPTER_OUT"
echo "merged:  $MERGED_OUT"
echo "epochs:  $EPOCHS"
echo "======================================================"

# --- guards ------------------------------------------------------------------
[ -f "$DATA" ] || { echo "ERROR: data file not found: $DATA"; exit 1; }
[ -d "$BASE" ] || { echo "ERROR: base model dir not found: $BASE (edit BASE=)"; exit 1; }
case "$DATA" in
  *v2*|*_v2_1*) echo "REFUSING: '$DATA' looks like a v2/v2.1 set. Phase-0 trains v1 voice only."; exit 1 ;;
esac
# v1 must be clean of the wrong-paradigm content
if grep -qiE "actually think|don't just perform|<think>|\[mood" "$DATA"; then
  echo "REFUSING: '$DATA' contains thinking/mood-on-command examples — not voice-only."; exit 1
fi

# --- 1) smoke ----------------------------------------------------------------
echo; echo "[1/3] smoke test (proves the toolchain runs)…"
python train/sft_lora.py --data "$DATA" --model "$BASE" --smoke

# --- 2) real train -----------------------------------------------------------
echo; echo "[2/3] training the frozen voice adapter (a few hours on a 4060)…"
python train/sft_lora.py \
  --data "$DATA" \
  --model "$BASE" \
  --out "$ADAPTER_OUT" \
  --epochs "$EPOCHS"

# --- 3) merge ----------------------------------------------------------------
echo; echo "[3/3] merging adapter into a standalone bf16 model…"
python scripts/posttrain/merge_lora_for_export.py \
  --base-model "$BASE" \
  --adapter "$ADAPTER_OUT" \
  --out "$MERGED_OUT" \
  --torch-dtype bfloat16 \
  --device-map "$MERGE_DEVICE_MAP"

echo
echo "================ DONE ================"
echo "Frozen voice adapter : $ADAPTER_OUT"
echo "Merged model to serve: $MERGED_OUT"
echo
echo "Next (manual):"
echo "  1) (optional) eval:  see step 3 in PHASE0_VOICE_RETRAIN.md"
echo "  2) serve:  python serve_elysia.py --model $MERGED_OUT --host 127.0.0.1 --port 8000"
echo "  3) run OLV (Windows):  uv run run_server.py   (conf.yaml already points at :8000/v1)"
