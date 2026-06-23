"""STT backend factory — pick a speech-to-text backend from config."""

from __future__ import annotations

from .base import STTBackend


def create_stt(config: dict) -> STTBackend:
    name = (config.get("stt_backend") or "faster-whisper").lower()

    if name in ("faster-whisper", "faster_whisper", "whisper"):
        from .faster_whisper_backend import FasterWhisperBackend
        return FasterWhisperBackend(
            model_size=config.get("stt_model", "base"),
            device=config.get("stt_device", "auto"),
            compute_type=config.get("stt_compute_type", "auto"),
            language=config.get("stt_language") or None,
        )

    raise ValueError(f"Unknown stt_backend: {name!r}. Use 'faster-whisper'.")
