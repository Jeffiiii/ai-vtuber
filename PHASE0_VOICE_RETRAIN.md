# Phase 0 — Freeze the voice (retrain on v1 data only)

**Goal (V3_DIRECTION §8 / INTEGRATION_BLUEPRINT Workstream A):** the model OLV serves
should carry **voice only** — cadence, warmth, bilingual switching, in-character refusals,
no markdown — and **nothing else**. The inner life comes from the *substrate* (memory,
mood, perception in the OLV plugin), never from the weights. So we retrain the LoRA on the
**v1** dataset and drop the v2 / v2.1 additions, then freeze the adapter and stop iterating
the dataset for "soul."

## Why this, exactly

| Dataset | Lines | What it adds | Use it? |
|---|---|---|---|
| `data/elysia_train.jsonl` (**v1**) | 393 | pure voice/disposition — greeting, chat, banter, comfort, boundaries | ✅ **train on this** |
| `data/elysia_train_v2.jsonl` | 669 | v1 + VIVID **mood-on-command** examples | ❌ performed affect |
| `data/elysia_train_v2_1.jsonl` | 821 | v2 + **thinking** examples ×4 upsample | ❌ performed introspection |

The model currently served (`output/elysia-merged-v2`) was built from the v2 line — i.e. the
wrong-paradigm weights this whole correction is about. v1 is verifiably clean: 0 thinking
prompts, 0 mood tags, 0 markdown, one consistent voice-only system prompt across all 393
lines.

**The training script is already Phase-0-correct** — it does completion-only loss (masks the
prompt, trains only her reply), a held-out val split with `eval_loss` + best-epoch selection,
and `enable_thinking=False` in the chat template. Nothing to change there; this is a *data*
decision.

---

## What you'll run (WSL2, the training venv)

All paths below assume:
- **repo:** `/mnt/c/Users/Leo12/Documents/ai-vtuber` (the Windows folder, seen from WSL)
- **base model:** `/home/leo12/models/Qwen3-4B` (from your v2 `merge_manifest.json`)
- **training venv:** `~/ai-vtuber/.venv-train`

If any of those differ on your box, adjust the path in the command — nothing else changes.

### 0) One-time: open WSL and activate the training env
```bash
source ~/ai-vtuber/.venv-train/bin/activate
cd /mnt/c/Users/Leo12/Documents/ai-vtuber
# offline so it uses your local base model, not the Hub
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
nvidia-smi >/dev/null && echo "GPU OK"
```

### 1) Smoke test the pipeline (≈2 min — proves the toolchain runs)
```bash
python train/sft_lora.py \
  --data data/elysia_train.jsonl \
  --model /home/leo12/models/Qwen3-4B \
  --smoke
```
Expect: `SMOKE OK — pipeline runs end to end.` If this fails, fix the environment before the
real run (it's almost always a torch/bitsandbytes CUDA issue — see Troubleshooting).

### 2) Real training run (a few hours on the 4060)
```bash
python train/sft_lora.py \
  --data data/elysia_train.jsonl \
  --model /home/leo12/models/Qwen3-4B \
  --out output/lora-elysia-v1voice \
  --epochs 3
```
Watch for, in the logs:
- `Training examples: ~353 | validation: ~40` (the val split is working)
- an `eval_loss` printed each epoch that **goes down then flattens** (best epoch is
  auto-loaded at the end; you're not blindly keeping the last, possibly-overfit one)

Output: the frozen voice adapter at `output/lora-elysia-v1voice/`.

### 3) (Recommended) Sanity-eval the adapter before merging
```bash
PYTHONPATH=scripts/posttrain python scripts/posttrain/post_train_health_check.py \
  --character elysia \
  --base-model /home/leo12/models/Qwen3-4B \
  --adapter output/lora-elysia-v1voice \
  --eval-file eval/elysia_eval.jsonl \
  --out posttrain_results/elysia_v1voice_health.jsonl \
  --limit 8 --load-4bit
```
Read a few generations in the output file. You want: in character, replies in the viewer's
language, no markdown, **no `<think>` and no performed introspection**. If she's reciting an
inner monologue, the wrong dataset got trained — confirm step 2 used `elysia_train.jsonl`.

### 4) Merge the adapter into a standalone bf16 model
```bash
python scripts/posttrain/merge_lora_for_export.py \
  --base-model /home/leo12/models/Qwen3-4B \
  --adapter output/lora-elysia-v1voice \
  --out output/elysia-merged-v1voice \
  --torch-dtype bfloat16 \
  --device-map auto
```
If the merge OOMs on the 8GB GPU, use `--device-map cpu` (slower, but merge doesn't need the
GPU). Output: `output/elysia-merged-v1voice/`.

### 5) Serve it (this is what OLV talks to)
```bash
python serve_elysia.py --model output/elysia-merged-v1voice --host 127.0.0.1 --port 8000
```
Leave this running. It exposes `/v1/chat/completions` (streaming), `/v1/models`, `/health`
with `enable_thinking=False` and Qwen3 non-thinking sampling — exactly what OLV expects.

**Smoke-test the endpoint** (any second terminal):
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"elysia-merged","messages":[{"role":"user","content":"hi elysia"}],"stream":false}'
```
You should get a short, warm, in-character line — no markdown, no `<think>`.

### 6) Run OLV against it (Windows PowerShell, in the OLV folder)
```powershell
cd C:\Users\Leo12\Documents\Open-LLM-VTuber
uv run run_server.py
```
No `conf.yaml` change is needed: it already points `openai_compatible_llm` at
`http://localhost:8000/v1`, and the served model name is arbitrary (the server serves one
model). Open the printed URL (default http://localhost:12393) and talk to her.

---

## Done when (Phase-0 acceptance)

1. **Smoke** prints `SMOKE OK`.
2. **Training** shows a real val split and an `eval_loss` that drops then flattens; the best
   epoch is auto-loaded.
3. **Health check / curl**: in-character, correct language, no markdown, **no `<think>`,
   no performed introspection**.
4. In **OLV** you hear a voice-correct reply with the avatar moving — and she is *not*
   narrating an inner life. (Her memory/mood/perception now come from the plugin substrate,
   which you validate separately.)

When all four pass, the voice is **frozen**. Stop iterating the dataset. From here, every
improvement happens in the substrate (memory, mood, perception), never by adding lines or a
"thinking" prompt — that's the regression the whole V3 direction is correcting.

---

## After it's validated (housekeeping)
- You can retire `output/elysia-merged-v2` and `output/lora-elysia-v2` once you're happy with
  v1voice (keep them until then as a fallback).
- The serve command is the only thing that names the model dir, so switching back is just
  changing `--model` — no OLV edits.

## Troubleshooting
- **`CUDA GPU not visible`** — inside WSL, `nvidia-smi` must work and torch must be the cu124
  build: `pip install torch --index-url https://download.pytorch.org/whl/cu124`.
- **bitsandbytes errors** — it behaves best under WSL2; reinstall `bitsandbytes>=0.43` in the
  same venv after torch.
- **It downloads from the Hub instead of using the local base** — make sure
  `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` are exported and `--model` points at the local
  `/home/leo12/models/Qwen3-4B` directory.
- **Merge OOM** — `--device-map cpu`.
- **She performs introspection again** — you trained the wrong file. It must be
  `data/elysia_train.jsonl` (v1), not the v2 / v2.1 files.

> One-shot option: `bash run_phase0_voice.sh` runs smoke → train → merge in sequence with
> these exact paths. Eval (step 3) and serve (step 5) stay manual on purpose.
