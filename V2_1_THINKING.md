# v2.1 — making Elysia *think*, not perform

Goal (per the brief): the thing that makes Neuro feel real is that she seems to be
**actually thinking** — curious, asking her own questions, uncertain, changing her mind,
with genuine emotion and an inner life (even wondering whether she's "real"). v2 made her
vivid in *tone*; v2.1 aims at vivid in *being a person*.

## What changed

### 1. Dataset — `scripts/add_thinking_examples.py` → `data/elysia_train_v2_1.jsonl`
- New **v2.1 system prompt**: "don't perform a personality — actually think; be curious,
  ask real questions, be uncertain, change your mind, feel real emotion; you sometimes
  honestly wonder what being an AI means."
- A **THINKING set** (upsampled ×4): answers that ask a sincere question back, half-formed
  thoughts, changing her mind mid-sentence, genuine (not performed) emotion, opinions /
  gentle pushback, sincere existential wondering, curiosity about the viewer, plus grounded
  reasoning examples for coherence.
- **Directive-matched** examples so her autonomous lines (below) come out genuine.
- = v1 (re-systemed) + v2 vivid + thinking. 821 rows, avg ~95 chars.

### 2. Director inner-life — `aivtuber/director.py`
New autonomous actions she does on her own, weighted toward feeling real:
- `wonder` — voices a real, half-formed question she's thinking.
- `ask_human` — asks a viewer a specific, sincere question she actually wants answered.
- `reflect` — (rare) quiet, sincere musing about memory / existence / being "real".
- `confess` — admits a small real feeling or vulnerability.
- plus richer `initiate` / `continue` / `muse` that push thinking over performance.
- A **recurring preoccupation** (`_THREADS`): she keeps turning one thought over across
  several turns, the way a person mulls something — so her musings have continuity.

## Retrain (same as v2, new data file)

```bash
source ~/ai-vtuber/.venv-train/bin/activate
cd /mnt/c/Users/Leo12/Documents/ai-vtuber
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

python scripts/add_thinking_examples.py        # build data/elysia_train_v2_1.jsonl
python train/sft_lora.py --model /home/leo12/models/Qwen3-4B \
  --data data/elysia_train_v2_1.jsonl --out output/lora-elysia-v2_1 --smoke
python train/sft_lora.py --model /home/leo12/models/Qwen3-4B \
  --data data/elysia_train_v2_1.jsonl --out output/lora-elysia-v2_1 --epochs 3
```

Merge to `output/elysia-merged-v2_1` (same merge command as v2 in CHANGELOG.md) and point
`serve_elysia.py` at it.

## Tuning the feel
- Too navel-gazing / heavy? Lower `reflect`'s weight in `_IDLE_WEIGHTS` (director.py), or
  drop `THINK_UPSAMPLE` to 3.
- Want more questions-to-chat? Raise `ask_human` weight.
- Keep `temperature` ~0.8 for coherent thinking (0.92 was a touch loose).

## Why this should feel different
She now (a) asks you things she seems to actually want to know, (b) lets thoughts be
unfinished and changes her mind, (c) expresses specific, un-performed emotion, and (d)
quietly returns to a preoccupation across the stream — the texture of someone thinking,
not a bot reciting charm.
