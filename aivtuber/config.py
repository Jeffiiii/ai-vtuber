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
    # local_http provider (serve_elysia.py — transformers backend, no GGUF/Ollama)
    "local_http_url": "http://127.0.0.1:8000",
    "local_http_timeout_s": 300,
    "persona_path": "persona/elysia.json",
    "temperature": 0.85,
    "max_tokens": 400,
    "max_turns": 12,
    "max_examples": 8,

    # --- Stage 2: voice (TTS) ---
    "voice_enabled": False,                 # voice_cli speaks replies when True
    "tts_backend": "xtts",                  # "xtts" (local, default) | "edge" (online)
    "tts_voice_en": "en-US-JennyNeural",
    "tts_voice_zh": "zh-CN-XiaoxiaoNeural",
    "tts_rate": "+0%",
    "tts_pitch": "+8Hz",                    # slight pitch-up for a cuter tone (edge)
    "xtts_speaker_wav": "",                 # path to a 6-20s clip to CLONE a voice (optional)
    "xtts_speaker": "Ana Florence",         # built-in XTTS voice used when no clip
    "xtts_model": "tts_models/multilingual/multi-dataset/xtts_v2",

    # --- Stage 2: ears (STT) ---
    "stt_backend": "faster-whisper",
    "stt_model": "base",                    # tiny|base|small|medium|large-v3
    "stt_device": "auto",
    "stt_compute_type": "auto",
    "stt_language": "",                     # "" = auto-detect EN/ZH

    # --- Stage 3: live (chat + avatar) ---
    "chat_source": "console",               # "console" | "twitch" | "bilibili"
    "twitch_token": "",                     # "oauth:xxxx" (chat scope)
    "twitch_channel": "",                   # your channel name
    "bilibili_room_id": 0,                  # your Bilibili live room id
    "avatar_backend": "web",                # "null" | "web" | "vtube-studio"
    "avatar_web_host": "127.0.0.1",
    "avatar_web_port": 8010,                # OBS Browser Source -> http://127.0.0.1:8010
    "avatar_name": "Elysia",
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

    # --- Stage 4: autonomy (the Director) ---
    "director_idle_seconds": 8.0,           # quiet time before she speaks unprompted
    "director_tick_seconds": 1.0,           # how often the loop checks
    "director_start_energy": 0.6,           # initial mood energy (0-1)
    "director_language": "zh",              # autonomous lines default language: zh | en

    # --- Stage 4: vision (senses) ---
    "vision_backend": "ocr",                # "ocr" | "vlm"
    "vision_region": None,                  # {"top","left","width","height"} or None=full
    "vision_ocr_langs": "eng+chi_sim",
    "vision_max_chars": 240,
    "vision_interval_s": 20,                # how often she glances at the screen
    "tesseract_cmd": "",                    # path to tesseract.exe on Windows if needed
    "vlm_endpoint": "",

    # --- Stage 4: games (hands) ---
    "guess_lo": 1,
    "guess_hi": 100,
    "game_dry_run": True,                   # external game: print keys instead of pressing
    "game_max_steps": 50,
    "game_use_vision": True,
    "game_actions": None,                   # {action: key} for external game, or None=default
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
