# Elysia — changelog & current tuning

## State (v2 live)
- **Brain:** fine-tuned **v2** vivid model — trained on `data/elysia_train_v2.jsonl` (669 rows:
  393 v1 re-systemed + 92 vivid mood-tagged ×3), adapter `output/lora-elysia-v2`, merged to
  `output/elysia-merged-v2`, served by `serve_elysia.py` on :8000.
- **Voice:** GPT-SoVITS **GSVI** v4 Elysia model (`models/v4/爱莉希雅`) on :8002, via `serve_tts.py`
  proxy on :8020. Per-request model reload patched out in `tools/my_infer.py` (cache).
- **Avatar/site:** website (`jeffi`) Live2D chat, served locally over http; desktop orchestrator
  uses web/VTS avatar.
- **Autonomy:** Director injects `[Mood: …]` notes; v2 was trained against them, so length/energy
  shift with mood (tender → hyper).
- **Scheduled job:** `elysia-inbox` runs hourly, processes `AGENT_INBOX.md`.

## Current config knobs (config.json) and why
- `gsvi_temperature: 0.7` — lowered from 1.0; her voice was **too enthusiastic**, this calms the prosody.
- `gsvi_speed: 1.0` — kept at normal (0.96 was tried and reverted; original speed was preferred).
- `gsvi_sample_steps: 8` — fast v4 diffusion (vs 16 = nicer but slower).
- `temperature: 0.92` — brain sampling. v2 is livelier but **slightly looser logic**; drop toward 0.8
  for tighter, more coherent replies.
- `max_tokens: 300`.

## Fixes applied
- **EN/ZH language drift:** website `ElysiaBrain.jsx` `buildMessages` now adds an explicit per-turn
  language directive ("the viewer's message is in English — reply in English"), so she stops
  answering English questions in Chinese. NOTE: the **desktop** `brain.py` doesn't have this guard
  yet — add it if she drifts when streaming from the orchestrator.
- **Streaming voice:** website + desktop synthesize sentence-by-sentence and play in order, so she
  starts talking after sentence 1 (sentence splitter handles 。！？…♪ and ". ! ?"+space, ignores decimals).

## Known trade-offs / dials
- Livelier personality ↔ slightly looser reasoning. Tighten: `temperature` 0.92 → 0.8, or rebuild the
  dataset with `UPSAMPLE = 2` (in `scripts/add_vivid_examples.py`) and retrain.
- Voice energy is set by the **reference clip** (currently the dramatic `由此点亮名为未来的奇迹`). For a
  calmer baseline, add a calm clip as a new emotion (`reference_audios/中文/emotions/【平静】<text>.wav`)
  and set `gsvi_emotion: 平静`; future: map Director mood → voice emotion.

## Long-term memory (new)
- Per-viewer profiles persist across sessions in `memory/longterm.json` (name, summary, facts).
  Brain recalls them when a viewer speaks and refreshes them via the LLM in the background.
  Desktop/orchestrator only for now. Config: `longterm_enabled`, `longterm_update_every`. See MEMORY.md.

## Overnight build — "make her think like a person" + Bilibili stream (new)
Goal from the brief: Neuro feels real because she seems to *think* — curious, asks her own
questions, uncertain, genuine emotion, an inner life (even wondering if she's "real").
- **v2.1 dataset** (`scripts/add_thinking_examples.py` → `data/elysia_train_v2_1.jsonl`, 821
  rows): new system prompt + a THINKING register (questions back, half-formed thoughts,
  changing her mind, real emotion, opinions, sincere existential wondering) + grounded
  reasoning. See V2_1_THINKING.md. **Retrain pending (you run it).**
- **Director inner-life** (`director.py`): new autonomous actions `wonder / ask_human /
  reflect / confess` + richer `initiate/continue/muse`, weighted toward feeling real;
  a recurring **preoccupation thread** so a thought carries across turns.
- **Mood → voice emotion**: GSVI `set_emotion`; orchestrator maps Director mood energy →
  reference emotion (tender→平静, warm→温柔, playful→默认, hyper→激动). Clips made from your
  recordings (calm/excited/gentle) + transcribed; default emotion set to 温柔 (calmer).
- **Attachment** (`memory.py`): fondness grows per returning visit and colors her recall.
- **Bilibili stream (full)**: operator **kill-switch** in the orchestrator (mute/pause/
  panic/quit), **`start_stream.ps1`** one-command launcher, and **STREAM_BILIBILI.md**
  (VTube Studio + VB-CABLE lip-sync + OBS scene + danmaku + go-live checklist).

## Dates
- 2026-06-25 — v2 trained (loss 4.7→0.32, ~20 min), merged, served. Voice/lang tuning above.
- 2026-06-25 — long-term per-viewer memory added (memory.py LongTermMemory + brain + orchestrator).
- 2026-06-25 (overnight) — v2.1 thinking dataset, Director inner-life, mood→voice emotion +
  emotion clips, attachment, Bilibili stream setup (kill-switch + launcher + guide).
