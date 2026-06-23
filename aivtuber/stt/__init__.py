"""Speech-to-text (Stage 2 — the ears).

Backend: faster-whisper (local, EN/ZH). `mic.py` captures audio from the microphone.
"""

from .base import STTBackend
from .factory import create_stt

__all__ = ["STTBackend", "create_stt"]
