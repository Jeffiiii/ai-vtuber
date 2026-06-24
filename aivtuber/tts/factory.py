"""TTS backend factory — pick a voice backend from config."""

from __future__ import annotations

from .base import TTSBackend


def create_tts(config: dict) -> TTSBackend:
    name = (config.get("tts_backend") or "xtts").lower()

    if name in ("edge", "edge-tts", "edgetts"):
        from .edge_tts_backend import EdgeTTSBackend
        return EdgeTTSBackend(
            voice_en=config.get("tts_voice_en", "en-US-JennyNeural"),
            voice_zh=config.get("tts_voice_zh", "zh-CN-XiaoxiaoNeural"),
            rate=config.get("tts_rate", "+0%"),
            pitch=config.get("tts_pitch", "+8Hz"),
        )

    if name in ("gsvi", "gpt-sovits-inference"):
        from .gsvi_backend import GSVIBackend
        return GSVIBackend(
            url=config.get("gsvi_url", "http://127.0.0.1:8002"),
            model_name=config.get("gsvi_model_name", ""),
            version=config.get("gsvi_version", "v4"),
            emotion=config.get("gsvi_emotion", "默认"),
            prompt_lang=config.get("gsvi_prompt_lang", "中文"),
            top_k=config.get("gsvi_top_k", 10),
            top_p=config.get("gsvi_top_p", 1.0),
            temperature=config.get("gsvi_temperature", 1.0),
            speed=config.get("gsvi_speed", 1.0),
            repetition_penalty=config.get("gsvi_repetition_penalty", 1.35),
            sample_steps=config.get("gsvi_sample_steps", 8),
        )

    if name in ("gptsovits", "gpt-sovits", "sovits"):
        from .gptsovits_backend import GPTSoVITSBackend
        return GPTSoVITSBackend(
            url=config.get("gptsovits_url", "http://127.0.0.1:9880"),
            ref_audio=config.get("gptsovits_ref_audio", ""),
            prompt_text=config.get("gptsovits_prompt_text", ""),
            prompt_lang=config.get("gptsovits_prompt_lang", "zh"),
            gpt_weights=config.get("gptsovits_gpt_weights", ""),
            sovits_weights=config.get("gptsovits_sovits_weights", ""),
            top_k=config.get("gptsovits_top_k", 15),
            top_p=config.get("gptsovits_top_p", 1.0),
            temperature=config.get("gptsovits_temperature", 1.0),
            speed=config.get("gptsovits_speed", 1.0),
            text_split_method=config.get("gptsovits_text_split", "cut5"),
        )

    if name in ("xtts", "coqui"):
        from .xtts_backend import XTTSBackend
        return XTTSBackend(
            speaker_wav=config.get("xtts_speaker_wav", ""),
            speaker=config.get("xtts_speaker", "Ana Florence"),
            model=config.get("xtts_model", "tts_models/multilingual/multi-dataset/xtts_v2"),
            device=config.get("xtts_device", "auto"),
            gen_params={
                "temperature": config.get("xtts_temperature"),
                "length_penalty": config.get("xtts_length_penalty"),
                "repetition_penalty": config.get("xtts_repetition_penalty"),
                "top_k": config.get("xtts_top_k"),
                "top_p": config.get("xtts_top_p"),
                "speed": config.get("xtts_speed"),
            },
        )

    raise ValueError(f"Unknown tts_backend: {name!r}. Use 'gptsovits', 'xtts', or 'edge'.")
