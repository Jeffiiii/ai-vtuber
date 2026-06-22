"""LLM provider interface.

Adapted from the Conference project's `conference/llm/base.py` so the rest of the
codebase can talk to any backend (local Ollama now; cloud APIs later) through one
small interface. Kept dependency-free.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Iterator


Message = dict  # {"role": "system"|"user"|"assistant", "content": str}


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def generate(self, messages: list[Message], temperature: float = 0.8,
                 max_tokens: int = 512) -> str:
        """Return the full reply for a list of chat messages."""
        ...

    def stream_generate(self, messages: list[Message], temperature: float = 0.8,
                        max_tokens: int = 512) -> Iterator[str]:
        """Yield reply text chunks. Default: fall back to non-streaming."""
        yield self.generate(messages, temperature, max_tokens)

    def generate_json(self, messages: list[Message], temperature: float = 0.0,
                      max_tokens: int = 512, max_retries: int = 2) -> dict | list:
        """Generate and parse JSON, repairing on failure. Useful later for tool
        calls / structured emotion tags."""
        for attempt in range(max_retries + 1):
            raw = self.generate(messages, temperature=temperature, max_tokens=max_tokens)
            parsed = self._try_parse_json(raw)
            if parsed is not None:
                return parsed
            if attempt < max_retries:
                messages = list(messages) + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "That was not valid JSON. Output ONLY "
                                                "the corrected JSON, no markdown, no prose."},
                ]
        return {}

    @abstractmethod
    def health_check(self) -> tuple[bool, str]:
        """Return (ok, human_readable_status)."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def is_local(self) -> bool: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    # ------------------------------------------------------------------
    @staticmethod
    def _try_parse_json(raw: str):
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(l for l in text.split("\n") if not l.startswith("```"))
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        for pattern in (r"\[.*\]", r"\{.*\}"):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    continue
        return None
