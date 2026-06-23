# The Full VTuber — Orchestration (Stage 4/5)

Everything wired into one loop: `aivtuber/orchestrator.py`. This is the capstone that
combines the fine-tuned brain, autonomy, chat, voice, ears, avatar, vision, games, and
moderation.

```
                        ┌─────────── chat in (console / Twitch / Bilibili) ──┐
   mic (STT, optional) ─┤                                                     │  moderation
                        │   screen (vision/OCR, optional) ──► observations    │  (in + out)
                        ▼                                                     ▼
                     ┌────────────────────── Director ──────────────────────┐
                     │ decides each tick: respond / event / observe /        │
                     │ initiate / ask / continue / muse   (+ mood, language) │
                     └───────────────────────┬───────────────────────────────┘
                                             ▼
                                   Brain (fine-tuned Elysia)
                                             ▼
                              reply ─► moderation ─► emotion + TTS
                                             ▼                 ▼
                                     avatar lip-sync     audio out
```

## Run it

The model server must be up first (WSL): `python serve_elysia.py --model …` (or Ollama),
and `config.json` set to that provider. Then:

```bash
# quietest test: console chat, web avatar, no voice
python -m aivtuber.orchestrator --no-voice

# full local character: console + web avatar + XTTS voice
python -m aivtuber.orchestrator

# read your Bilibili room (set bilibili_room_id in config.json)
python -m aivtuber.orchestrator --platform bilibili

# let her comment on your screen (needs OCR extras + tesseract)
python -m aivtuber.orchestrator --vision

# talk to her by microphone (needs STT extras)
python -m aivtuber.orchestrator --listen

# play a game in character (no chat)
python -m aivtuber.orchestrator --game tictactoe
python -m aivtuber.orchestrator --game guessing
python -m aivtuber.orchestrator --game external      # dry-run by default

# everything at once
python -m aivtuber.orchestrator --platform bilibili --vision --listen
```

`/quit` ends it. Everything degrades gracefully — if an extra isn't installed, that
feature just turns off and the rest keeps running.

## The pieces

| Capability | Module | Notes |
|---|---|---|
| Brain | `llm/` + fine-tuned model | served by `serve_elysia.py` or Ollama |
| Autonomy | `director.py` | talks on her own; mood; **Chinese default**, English when a viewer uses it |
| Chat in | `chat/` | console, Twitch, **Bilibili** danmaku |
| Voice out | `tts/` (XTTS default) | local, offline; built-in voice or clone via `xtts_speaker_wav` |
| Ears | `stt/` (faster-whisper) | `--listen` |
| Avatar | `avatar/` | **web** (built-in lip-sync face) or VTube Studio |
| Senses | `vision/` (OCR) | `--vision`; reads on-screen text → she comments |
| Hands | `games/` | guessing, tic-tac-toe (play now); external-game scaffold |
| Safety | `moderation.py` | screens viewer input AND her output (always on) |

## Install extras (only what you use)

```bash
pip install -r requirements-voice.txt     # XTTS voice (+ STT for --listen)
pip install -r requirements-stream.txt    # Bilibili/Twitch, VTube Studio, OCR vision, pyautogui
```
For OCR vision you also need the Tesseract binary (Windows installer adds it; set
`tesseract_cmd` in config if it isn't on PATH).

## The built-in avatar in OBS

`--avatar web` serves a lip-sync face at `http://127.0.0.1:8010` on a green background.
In OBS: add a **Browser Source** with that URL, then chroma-key out the green. Her mouth
flaps while speaking and cheeks/brows shift with emotion. Swap to `--avatar vtube-studio`
when you have a real Live2D model (see STAGE3.md for the VTS + virtual-audio-cable wiring).

## Safety reminder

Moderation here is a starter net (keyword + heuristics in `moderation.py`) — extend the
word lists for your community, and keep a human kill-switch when live to a public room.
An unscripted model will eventually say something you didn't intend.

## What's still "to taste"

- **Longer/chattier lines** — she's terse from the short training data. Bump `max_tokens`
  + relax the persona length rule, or train a v2 dataset with longer examples.
- **Real scene vision** — swap OCR for a Qwen2.5-VL endpoint (`vision/vlm.py`).
- **Long-term memory** — wire `LongTermMemory` to embeddings/FAISS for cross-session recall.
- **Streaming voice + barge-in** — start speaking before generation finishes; let her be
  interrupted (this is where adopting Open-LLM-VTuber's voice layer pays off).
