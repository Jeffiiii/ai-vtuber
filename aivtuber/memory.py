"""Conversation memory.

Stage 1: short-term rolling history (implemented).
Stage 4: long-term vector memory — you can plug in the Conference project's
`semantic/` stack (sentence-transformers embeddings + FAISS) behind the same
interface later. A stub is left below to mark the seam.
"""

from __future__ import annotations

from collections import deque


class ShortTermMemory:
    """A rolling window of recent turns kept inside the context window."""

    def __init__(self, max_turns: int = 12):
        # one "turn" = one message (user OR assistant)
        self._buf: deque[dict] = deque(maxlen=max_turns * 2)

    def add(self, role: str, content: str):
        self._buf.append({"role": role, "content": content})

    def messages(self) -> list[dict]:
        return list(self._buf)

    def clear(self):
        self._buf.clear()


class LongTermMemory:
    """Placeholder for Stage 4. Wire to Conference's semantic/vector_store.py later.

    Intended interface:
        remember(text)          -> store a fact/embedding
        recall(query, k=3)      -> list[str] of relevant past facts
    """

    def remember(self, text: str) -> None:  # pragma: no cover - not yet implemented
        pass

    def recall(self, query: str, k: int = 3) -> list[str]:  # pragma: no cover
        return []
