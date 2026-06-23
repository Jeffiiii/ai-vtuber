"""Text-to-speech interface (Stage 2 — the voice).

A small ABC so the rest of the app can synthesize speech through any backend
(edge-tts now; Coqui XTTS for local/voice-cloning), mirroring the LLM provider
pattern. Language is auto-detected so Elysia speaks EN or ZH to match her reply.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


def detect_lang(text: str) -> str:
    """Return 'zh' if the text is mostly Chinese, else 'en'. Cheap heuristic."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    return "zh" if cjk > latin else "en"


class TTSBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        """Write speech audio for `text` to `out_path`; return the path actually written
        (extension may differ per backend, e.g. .mp3 vs .wav)."""
        ...

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """(ok, message). False if the backend's package/config isn't ready."""
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def output_ext(self) -> str:
        return ".wav"
