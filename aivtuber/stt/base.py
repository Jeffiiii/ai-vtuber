"""Speech-to-text interface (Stage 2 — the ears).

A small ABC so the app can transcribe mic/audio through any backend
(faster-whisper now). Mirrors the TTS/LLM provider pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class STTBackend(ABC):
    @abstractmethod
    def transcribe(self, wav_path: str) -> str:
        """Transcribe a 16 kHz mono WAV file to text (auto-detects EN/ZH)."""
        ...

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...
