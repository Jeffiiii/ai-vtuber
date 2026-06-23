"""Avatar control interface (Stage 3).

Drives a Live2D avatar's expressions in response to Elysia's emotion. The default
implementation talks to VTube Studio's plugin API over websocket.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AvatarController(ABC):
    @abstractmethod
    def connect(self) -> tuple[bool, str]:
        """Establish the connection / authenticate. (ok, message)."""
        ...

    @abstractmethod
    def set_emotion(self, emotion: str) -> None:
        """Trigger the expression matching an emotion label (best-effort)."""
        ...

    def close(self) -> None:
        """Optional cleanup."""

    @property
    @abstractmethod
    def name(self) -> str: ...


class NullAvatar(AvatarController):
    """No-op avatar — prints the emotion. Lets the live loop run with no VTube
    Studio attached (handy for testing voice + chat first)."""

    def connect(self) -> tuple[bool, str]:
        return True, "null avatar (no VTube Studio; emotions printed only)"

    def set_emotion(self, emotion: str) -> None:
        print(f"[avatar] emotion -> {emotion}")

    @property
    def name(self) -> str:
        return "null"
