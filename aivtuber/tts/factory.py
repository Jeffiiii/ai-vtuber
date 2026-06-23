"""TTS backend factory — pick a voice backend from config."""

from __future__ import annotations

from .base import TTSBackend


def create_tts(config: dict) -> TTSBackend:
    name = (config.get("tts_backend") or "edge").lower()

    if name in ("edge", "edge-tts", "edgetts"):
        from .edge_tts_backend import EdgeTTSBackend
        return EdgeTTSBackend(
            voice_en=config.get("tts_voice_en", "en-US-JennyNeural"),
            voice_zh=config.get("tts_voice_zh", "zh-CN-XiaoxiaoNeural"),
            rate=config.get("tts_rate", "+0%"),
            pitch=config.get("tts_pitch", "+8Hz"),
        )

    if name in ("xtts", "coqui"):
        from .xtts_backend import XTTSBackend
        return XTTSBackend(
            speaker_wav=config.get("xtts_speaker_wav", ""),
            model=config.get("xtts_model", "tts_models/multilingual/multi-dataset/xtts_v2"),
        )

    raise ValueError(f"Unknown tts_backend: {name!r}. Use 'edge' or 'xtts'.")
