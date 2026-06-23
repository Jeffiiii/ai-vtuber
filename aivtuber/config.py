"""Config loading: defaults <- config.json (optional) <- env overrides."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "llm_provider": "ollama",
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "qwen3:8b",
    "ollama_num_ctx": 4096,
    "ollama_keep_alive": "30m",
    "ollama_timeout_s": 300,
    "ollama_auto_start": True,
    "ollama_auto_pull": True,
    "ollama_think": False,
    "persona_path": "persona/elysia.json",
    "temperature": 0.85,
    "max_tokens": 400,
    "max_turns": 12,
    "max_examples": 8,

    # --- Stage 2: voice (TTS) ---
    "voice_enabled": False,                 # voice_cli speaks replies when True
    "tts_backend": "edge",                  # "edge" (free, online) | "xtts" (local clone)
    "tts_voice_en": "en-US-JennyNeural",
    "tts_voice_zh": "zh-CN-XiaoxiaoNeural",
    "tts_rate": "+0%",
    "tts_pitch": "+8Hz",                    # slight pitch-up for a cuter tone
    "xtts_speaker_wav": "",                 # path to a reference clip (xtts only)
    "xtts_model": "tts_models/multilingual/multi-dataset/xtts_v2",

    # --- Stage 2: ears (STT) ---
    "stt_backend": "faster-whisper",
    "stt_model": "base",                    # tiny|base|small|medium|large-v3
    "stt_device": "auto",
    "stt_compute_type": "auto",
    "stt_language": "",                     # "" = auto-detect EN/ZH

    # --- Stage 3: live (chat + avatar) ---
    "chat_source": "console",               # "console" | "twitch"
    "twitch_token": "",                     # "oauth:xxxx" (chat scope)
    "twitch_channel": "",                   # your channel name
    "avatar_backend": "null",               # "null" | "vtube-studio"
    "vts_url": "ws://localhost:8001",
    # emotion label -> VTube Studio hotkey NAME (create these hotkeys in VTS)
    "avatar_expressions": {
        "happy": "Happy",
        "sad": "Sad",
        "surprised": "Surprised",
        "shy": "Shy",
        "playful": "Playful",
        "neutral": "Neutral",
    },
}


def load_config(path: str | Path = "config.json") -> dict:
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    # env overrides (handy on a new machine)
    if os.getenv("AIVT_MODEL"):
        cfg["ollama_model"] = os.environ["AIVT_MODEL"]
    if os.getenv("AIVT_PERSONA"):
        cfg["persona_path"] = os.environ["AIVT_PERSONA"]
    return cfg
