"""Vision backend factory."""

from __future__ import annotations

from .base import ScreenDescriber


def create_vision(config: dict) -> ScreenDescriber:
    name = (config.get("vision_backend") or "ocr").lower()

    if name == "ocr":
        from .ocr import OCRDescriber
        return OCRDescriber(
            region=config.get("vision_region") or None,
            langs=config.get("vision_ocr_langs", "eng+chi_sim"),
            max_chars=int(config.get("vision_max_chars", 240)),
            tesseract_cmd=config.get("tesseract_cmd", ""),
        )

    if name in ("vlm", "qwen-vl"):
        from .vlm import VLMDescriber
        return VLMDescriber(endpoint=config.get("vlm_endpoint", ""),
                            region=config.get("vision_region") or None)

    raise ValueError(f"Unknown vision_backend: {name!r}. Use 'ocr' or 'vlm'.")
