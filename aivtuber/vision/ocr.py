"""OCR screen describer — reads visible on-screen text.

Install: pip install mss pytesseract pillow   (+ the Tesseract binary:
  Windows: https://github.com/UB-Mannheim/tesseract/wiki ; then set tesseract_cmd
  Linux:   sudo apt install tesseract-ocr tesseract-ocr-chi-sim)

Captures a screen region, OCRs it (English + Simplified Chinese), and returns a
trimmed snippet. Cheap 'sense' that works with the text model — Elysia can react to
chat overlays, game text, subtitles, code on screen, etc.
"""

from __future__ import annotations

from .base import ScreenDescriber


class OCRDescriber(ScreenDescriber):
    def __init__(self, region: dict | None = None, langs: str = "eng+chi_sim",
                 max_chars: int = 240, tesseract_cmd: str = ""):
        # region: {"top","left","width","height"} or None for full primary monitor
        self.region = region
        self.langs = langs
        self.max_chars = max_chars
        self.tesseract_cmd = tesseract_cmd

    def describe(self) -> str:
        import mss          # lazy
        import pytesseract
        from PIL import Image

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        with mss.mss() as sct:
            mon = self.region or sct.monitors[1]   # [1] = primary monitor
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

        try:
            text = pytesseract.image_to_string(img, lang=self.langs)
        except Exception:
            text = pytesseract.image_to_string(img)  # fall back to default lang
        text = " ".join(text.split())               # collapse whitespace
        if not text:
            return ""
        if len(text) > self.max_chars:
            text = text[:self.max_chars] + "…"
        return text

    def is_available(self) -> tuple[bool, str]:
        try:
            import mss  # noqa: F401
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            return False, "Install: pip install mss pytesseract pillow (+ tesseract binary)"
        return True, "OCR screen reader ready"

    @property
    def name(self) -> str:
        return "ocr"
