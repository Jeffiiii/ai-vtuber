"""The Brain: ties persona + memory + LLM into a conversation loop.

Supports two kinds of turns:
  * reply_stream(user_text)   — respond to a real viewer message (stored as a
                                user turn in memory).
  * perform_stream(directive) — act on an internal "stage direction" from the
                                Director (autonomous lines: start a topic, ask
                                chat, continue a thread, react). The directive is
                                NOT stored; only Elysia's line is remembered.

`set_note()` injects a transient context line (e.g. current mood) for the next turns.
"""

from __future__ import annotations

import re
from typing import Iterator

from .llm.base import LLMProvider
from .memory import ShortTermMemory
from .persona import Persona

# Qwen3 (non-thinking) emits a leading "<think> ... </think>" block. Ollama strips
# it when think:false, but raw generations include it — scrub it so it never reaches
# the console, TTS, or memory.
_THINK_RE = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text)


class Brain:
    def __init__(self, provider: LLMProvider, persona: Persona,
                 memory: ShortTermMemory | None = None,
                 temperature: float = 0.85, max_tokens: int = 400,
                 max_examples: int = 8):
        self.provider = provider
        self.persona = persona
        self.memory = memory or ShortTermMemory()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_examples = max_examples
        self._system = persona.system_prompt()
        # Small varied sample of examples primes the voice without flooding context.
        self._examples = persona.example_messages(limit=max_examples, shuffle=True)
        self._note = ""           # transient context (mood/stage state)
        self._last_full = ""      # last fully-cleaned reply (set by _stream_clean)

    def set_note(self, note: str) -> None:
        """Set a transient context line injected into the next turn(s) (e.g. mood)."""
        self._note = note or ""

    # ------------------------------------------------------------------
    def _compose(self, turn_text: str) -> list[dict]:
        msgs = [{"role": "system", "content": self._system}]
        if self._note:
            msgs.append({"role": "system", "content": self._note})
        msgs += self._examples
        msgs += self.memory.messages()
        msgs.append({"role": "user", "content": turn_text})
        return msgs

    def _stream_clean(self, messages: list[dict],
                      max_tokens: int | None = None) -> Iterator[str]:
        """Stream provider output, suppressing any leading <think>...</think> block.
        Stores the fully-cleaned text in self._last_full."""
        chunks: list[str] = []
        buffer = ""
        started = False
        for piece in self.provider.stream_generate(
                messages, temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens):
            chunks.append(piece)
            if started:
                yield piece
                continue
            buffer += piece
            if "<think>" in buffer and "</think>" not in buffer:
                continue  # inside an unterminated think block
            cleaned = _strip_think(buffer)
            if cleaned:
                started = True
                yield cleaned
        self._last_full = _strip_think("".join(chunks)).strip()

    # ------------------------------------------------------------------
    def reply_stream(self, user_text: str) -> Iterator[str]:
        """Respond to a real viewer message; remembers both turns."""
        yield from self._stream_clean(self._compose(user_text))
        self.memory.add("user", user_text)
        self.memory.add("assistant", self._last_full)

    def perform_stream(self, directive: str,
                       max_tokens: int | None = None) -> Iterator[str]:
        """Act on an internal stage direction; remembers only Elysia's line."""
        yield from self._stream_clean(self._compose(directive), max_tokens=max_tokens)
        self.memory.add("assistant", self._last_full)

    def reply(self, user_text: str) -> str:
        return "".join(self.reply_stream(user_text)).strip()
