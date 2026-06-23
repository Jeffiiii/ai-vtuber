"""The Brain: ties persona + memory + LLM into a conversation loop.

This is the Stage 1 MVP "brain." Voice (TTS), avatar, and chat ingestion all hang
off of `reply_stream` later.
"""

from __future__ import annotations

from typing import Iterator

from .llm.base import LLMProvider
from .memory import ShortTermMemory
from .persona import Persona


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
        # Inject only a small, varied sample of the (possibly large) example set —
        # enough to prime the voice without flooding the context window. Sampled once
        # per session for consistency; the full set is best used as fine-tuning data.
        self._examples = persona.example_messages(limit=max_examples, shuffle=True)

    def _build_messages(self, user_text: str) -> list[dict]:
        msgs = [{"role": "system", "content": self._system}]
        msgs += self._examples            # few-shot voice priming
        msgs += self.memory.messages()    # recent real conversation
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def reply_stream(self, user_text: str) -> Iterator[str]:
        """Stream the character's reply, updating memory when done."""
        messages = self._build_messages(user_text)
        chunks: list[str] = []
        for piece in self.provider.stream_generate(
                messages, temperature=self.temperature, max_tokens=self.max_tokens):
            chunks.append(piece)
            yield piece
        full = "".join(chunks).strip()
        self.memory.add("user", user_text)
        self.memory.add("assistant", full)

    def reply(self, user_text: str) -> str:
        return "".join(self.reply_stream(user_text)).strip()
