"""Avatar control interface (Stage 3).

Drives an avatar's expressions + mouth in response to Elysia. Implementations:
NullAvatar (prints), VTubeStudioAvatar (real Live2D via plugin API), WebAvatar
(built-in lip-sync face you can drop into OBS as a browser source).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AvatarController(ABC):
    @abstractmethod
    def connect(self) -> tuple[bool, str]:
        ...

    @abstractmethod
    def set_emotion(self, emotion: str) -> None:
        ...

    # Mouth control — called by the loop around speech. Default no-ops so existing
    # backends keep working.
    def speak_start(self) -> None:
        ...

    def speak_end(self) -> None:
        ...

    def close(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class NullAvatar(AvatarController):
    """No-op avatar — prints the emotion. Lets the loop run with no avatar attached."""

    def connect(self) -> tuple[bool, str]:
        return True, "null avatar (no display; emotions printed only)"

    def set_emotion(self, emotion: str) -> None:
        print(f"[avatar] emotion -> {emotion}")

    @property
    def name(self) -> str:
        return "null"
