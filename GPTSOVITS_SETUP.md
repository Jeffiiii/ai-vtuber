# Elysia's voice with GPT-SoVITS (local, character-accurate)

GPT-SoVITS gives a purpose-trained, genuinely-Elysia voice that runs locally on
your 4060 and is fast enough for live. The app talks to GPT-SoVITS over HTTP, so
once it's running you just flip `tts_backend` and both the desktop app and the
website use it.

## 1. Install GPT-SoVITS

Easiest in China: download the **one-click 整合包** (integrated package) for
RVC-Boss/GPT-SoVITS (search "GPT-SoVITS 整合包"; the author distributes via
百度网盘/夸克). Unzip it — it bundles Python + CUDA, no environment setup.

(Or clone https://github.com/RVC-Boss/GPT-SoVITS and follow its README.)

## 2. Get an Elysia model

You need two weight files:
- a **GPT** weight: `…-e15.ckpt`
- a **SoVITS** weight: `…_e8_s208.pth`

Either **download a community Elysia model** (people share trained Elysia GPT-SoVITS
models on bilibili / ModelScope / huggingface — look for "爱莉希雅 GPT-SoVITS 模型"),
or **train your own** in the GPT-SoVITS WebUI from ~10-60 min of clean Elysia audio
(its UI walks you through slicing → ASR → train; ~30 min on your GPU).

You also need a **reference clip**: one clean, continuous **3–10 s** clip of Elysia
talking, plus its **exact transcript**. (See the note below — this is what your
current sample got wrong.)

## 3. Start the GPT-SoVITS API

In the GPT-SoVITS folder:

```
python api_v2.py
# serves http://127.0.0.1:9880
```

Load your weights either in its config (`GPT_SoVITS/configs/tts_infer.yaml`) or let
this app load them for you via the config keys below.

## 4. Point the app at it (config.json)

```json
{
  "tts_backend": "gptsovits",
  "gptsovits_url": "http://127.0.0.1:9880",
  "gptsovits_ref_audio": "C:/Users/Leo12/Documents/ai-vtuber/voice/elysia_ref.wav",
  "gptsovits_prompt_text": "大家好呀，今天也要元气满满地开始新的一天呢",
  "gptsovits_prompt_lang": "zh",
  "gptsovits_gpt_weights": "C:/path/to/elysia-e15.ckpt",
  "gptsovits_sovits_weights": "C:/path/to/elysia_e8_s208.pth"
}
```

- `gptsovits_ref_audio` / `gptsovits_prompt_text` — the reference clip and its EXACT
  transcript. The transcript must match the audio word-for-word.
- `gptsovits_gpt_weights` / `gptsovits_sovits_weights` — optional; if set, the app
  auto-loads them into the server on first synth. Leave blank if you set them in
  GPT-SoVITS's own config.

Then:
- **Desktop:** `python -m aivtuber.orchestrator` → Elysia voice.
- **Website:** `python serve_tts.py` (same venv) → the site uses it too. Hard-refresh.

## ⚠️ About your current sample (why cloning was weak)

Your uploaded clip was 15 s but **mostly silence — the longest continuous speech was
only 2.3 s**, and it was quiet (−32 dBFS). Any cloner needs ONE unbroken **5–10 s**
chunk of talking at a healthy level.

For the reference clip, record/rip:
- **One continuous 5–10 s** stretch of Elysia *talking* — a full sentence or two that
  flow together, **no long pauses**.
- A **clean source** (a voice line / story audio without BGM or battle SFX), not a
  speaker-and-room recording.
- A **normal, steady tone** (not shouting/singing).
- Then write its exact transcript for `gptsovits_prompt_text`.

For *training* your own model you want more (10–60 min), but the **inference reference**
is just that one good 3–10 s clip.

## Tuning

If output is unstable, in config: lower `gptsovits_temperature` (e.g. 0.6), adjust
`gptsovits_top_k` (10–20), `gptsovits_speed` (0.9–1.1). Restart after changes.
