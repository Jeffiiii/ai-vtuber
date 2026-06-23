"""Vision (Stage 4 — senses). Backends: ocr (on-screen text), vlm (scene, stub)."""

from .base import ScreenDescriber
from .factory import create_vision

__all__ = ["ScreenDescriber", "create_vision"]
