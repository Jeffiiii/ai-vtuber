# Stage 2 — Giving Elysia a Voice (and Ears)

This stage is **scaffolded and ready**. The text app is unchanged; voice is purely
additive and only activates when you install the optional packages.

## What's here

```
aivtuber/
├─ tts/                     # voice OUT
│  ├─ base.py               #   TTSBackend ABC + detect_lang() (EN/ZH)
│  ├─ edge_tts_backend.py   #   edge-tts: free, online, bilingual  ← default
│  ├─ xtts_backend.py       #   Coqui XTTS v2: local, voice-cloning
│  └─ factory.py
├─ stt/                     # ears (voice IN)
│  ├─ base.py               #   STTBackend ABC
│  ├─ faster_whisper_backend.py
│  ├─ mic.py                #   microphone capture (fixed / stop-on-silence)
│  └─ factory.py
├─ audio.py                 # plays the synthesized audio (Windows-friendly)
└─ voice_cli.py             # chat where Elysia SPEAKS her replies  ← run this
```

All voice settings live in `config.py` / `config.elysia.json` (keys prefixed
`tts_*`, `stt_*`, `voice_*`).

## Try it (after fine-tuning, or any time)

```powershell
# 1) install the voice extras (uses your TUNA mirror in China)
pip install -r requirements-voice.txt

# 2) hear Elysia speak her replies (type your messages)
python -m aivtuber.voice_cli

# 3) talk to her with your microphone (push-to-talk)
python -m aivtuber.voice_cli --listen
```

`edge-tts` is the default voice (free, needs internet, great EN + ZH). It auto-picks
an English or Chinese voice to match each reply. Tune the voice/pitch in config:
`tts_voice_en`, `tts_voice_zh`, `tts_pitch`. Browse voices with `edge-tts --list-voices`.

For a **custom/cloned** voice (fully local), switch `"tts_backend": "xtts"` and set
`"xtts_speaker_wav"` to a 6-20s clip of the target voice.

## How it fits together

```
mic → STT (faster-whisper) ─┐
                            ├→ Brain (persona + Ollama) → reply text
keyboard ───────────────────┘                               │
                                                            ▼
                              TTS (edge/xtts) → audio file → audio.play()
```

The same `Brain` from Stage 1 drives everything; voice just wraps its input/output.

## The real challenge here: latency

Right now it's reply-then-speak (simple, a couple seconds). For a live, natural feel
later you'll want to **stream**: start TTS on the first sentence while the LLM is still
generating, and add barge-in (let the viewer interrupt). That, plus echo cancellation,
is where the Open-LLM-VTuber project has solved hard problems worth borrowing — see the
earlier notes on adopting its voice layer.

## Next after voice (Stage 3 — avatar & live)

- Route TTS audio through a **virtual audio cable** (VB-Audio) so a **Live2D** model in
  **VTube Studio** lip-syncs to Elysia's speech.
- **OBS** for the stream layout; ingest **Twitch/YouTube/Bilibili** chat into the Brain.
- Map an "emotion" tag from the LLM to Live2D expressions.

These are native-app + streaming tasks (not pip installs), so they come once the voice
feels right.
