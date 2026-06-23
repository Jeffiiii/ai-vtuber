"""Vision-Language-Model screen describer (scaffold).

For true scene understanding (not just text), describe the screenshot with a VLM
such as Qwen2.5-VL. Two ways to wire it later:
  1) Run a VLM in serve_elysia.py-style server and POST the image here.
  2) Use a cloud VLM API.

Left as a stub so the interface exists now; OCRDescriber covers the text case today.
"""

from __future__ import annotations

from .base import ScreenDescriber


class VLMDescriber(ScreenDescriber):
    def __init__(self, endpoint: str = "", region: dict | None = None):
        self.endpoint = endpoint
        self.region = region

    def describe(self) -> str:  # pragma: no cover - not implemented yet
        return ""

    def is_available(self) -> tuple[bool, str]:
        return False, ("VLM describer not implemented yet. Use 'ocr' for now, or wire a "
                       "Qwen2.5-VL endpoint here.")

    @property
    def name(self) -> str:
        return "vlm"
