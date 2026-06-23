"""Live chat ingestion interface (Stage 3).

A ChatSource yields incoming viewer messages from a platform (Twitch/YouTube/
Bilibili) or the console (for testing). The live loop pulls messages from here and
feeds chosen ones to the Brain.
"""

from __future__ import annotations

import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    user: str
    text: str
    platform: str = "unknown"


class ChatSource(ABC):
    """Base class. Implementations push ChatMessage objects into `self._q`;
    the live loop drains them with get_nowait()/drain()."""

    def __init__(self):
        self._q: "queue.Queue[ChatMessage]" = queue.Queue()

    @abstractmethod
    def start(self) -> None:
        """Begin receiving messages (e.g. connect + run client in a thread)."""
        ...

    def stop(self) -> None:
        """Optional cleanup."""

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    # --- helpers used by the live loop ---
    def get_nowait(self) -> ChatMessage | None:
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def drain(self, limit: int = 50) -> list[ChatMessage]:
        out = []
        for _ in range(limit):
            m = self.get_nowait()
            if m is None:
                break
            out.append(m)
        return out
