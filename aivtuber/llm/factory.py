"""LLM provider factory — pick a backend from config.

Mirrors the Conference project's factory so adding cloud providers later (DeepSeek,
OpenAI, Anthropic, Gemini) is a one-branch change.
"""

from __future__ import annotations

import logging

from .base import LLMProvider

log = logging.getLogger("aivtuber")


def create_provider(config: dict) -> LLMProvider:
    name = (config.get("llm_provider") or "ollama").lower()

    if name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(
            base_url=config.get("ollama_base_url", "http://127.0.0.1:11434"),
            model=config.get("ollama_model", "qwen3:8b"),
            timeout=int(config.get("ollama_timeout_s", 300)),
            num_ctx=int(config.get("ollama_num_ctx", 4096)),
            keep_alive=config.get("ollama_keep_alive", "30m"),
            auto_start=bool(config.get("ollama_auto_start", True)),
            auto_pull=bool(config.get("ollama_auto_pull", True)),
            think=bool(config.get("ollama_think", False)),
        )

    if name in ("local_http", "local-http", "http", "server"):
        from .http_provider import LocalHTTPProvider
        return LocalHTTPProvider(
            url=config.get("local_http_url", "http://127.0.0.1:8000"),
            timeout=int(config.get("local_http_timeout_s", 300)),
        )

    # Placeholder for future cloud providers — wire up like Conference's DeepSeek.
    raise ValueError(f"Unknown or not-yet-implemented LLM provider: {name!r}. "
                     f"Use 'ollama' or 'local_http'.")
