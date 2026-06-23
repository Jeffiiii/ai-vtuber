"""Vision interface (Stage 4 — senses).

A ScreenDescriber turns what's on screen into a short text description that gets fed
to the brain as an observation, so Elysia can react to what's happening (a game, a
video, your desktop). Backends:
  * OCRDescriber  — reads on-screen TEXT (mss + tesseract). Works with the text model.
  * VLMDescriber  — describes the scene with a vision model (stub; wire later).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenDescriber(ABC):
    @abstractmethod
    def describe(self) -> str:
        """Capture the screen (or region) and return a short text description.
        Return '' if nothing useful is seen."""
        ...

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...
