"""Text-to-speech (Stage 2 — the voice).

Backends: edge-tts (free, online, EN/ZH) and Coqui XTTS v2 (local, voice-cloning).
Route output through a virtual audio cable later so a Live2D avatar can lip-sync.
"""

from .base import TTSBackend, detect_lang
from .factory import create_tts

__all__ = ["TTSBackend", "detect_lang", "create_tts"]
