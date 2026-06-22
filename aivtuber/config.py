"""Config loading: defaults <- config.json (optional) <- env overrides."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "llm_provider": "ollama",
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "qwen2.5:7b-instruct",
    "ollama_num_ctx": 4096,
    "ollama_keep_alive": "30m",
    "ollama_timeout_s": 300,
    "ollama_auto_start": True,
    "ollama_auto_pull": True,
    "persona_path": "persona/default.json",
    "temperature": 0.85,
    "max_tokens": 400,
    "max_turns": 12,
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
