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

import json
import re
import threading
from typing import Iterator

from .llm.base import LLMProvider
from .memory import LongTermMemory, ShortTermMemory
from .persona import Persona

# Qwen3 (non-thinking) emits a leading "<think> ... </think>" block. Ollama strips
# it when think:false, but raw generations include it — scrub it so it never reaches
# the console, TTS, or memory.
_THINK_RE = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text)


def _extract_json(text: str):
    """Pull the first balanced {...} object out of a model reply and parse it."""
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    return None
    return None


class Brain:
    def __init__(self, provider: LLMProvider, persona: Persona,
                 memory: ShortTermMemory | None = None,
                 temperature: float = 0.85, max_tokens: int = 400,
                 max_examples: int = 8,
                 longterm: LongTermMemory | None = None,
                 longterm_update_every: int = 4):
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
        # --- long-term, per-viewer memory (optional) ---
        self.longterm = longterm
        self.longterm_update_every = max(1, longterm_update_every)
        self.current_user = None  # who we're talking to right now
        self._recall = ""         # recalled profile line for current_user

    def set_note(self, note: str) -> None:
        """Set a transient context line injected into the next turn(s) (e.g. mood)."""
        self._note = note or ""

    def set_speaker(self, user: str | None) -> None:
        """Tell the brain which viewer it's talking to, so it recalls their memory."""
        self.current_user = user
        self._recall = self.longterm.recall_text(user) if (self.longterm and user) else ""

    # ------------------------------------------------------------------
    def _compose(self, turn_text: str, recall: str = "") -> list[dict]:
        msgs = [{"role": "system", "content": self._system}]
        if self._note:
            msgs.append({"role": "system", "content": self._note})
        if recall:
            msgs.append({"role": "system", "content": recall})
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
        """Respond to a real viewer message; remembers both turns (short + long term)."""
        yield from self._stream_clean(self._compose(user_text, recall=self._recall))
        self.memory.add("user", user_text)
        self.memory.add("assistant", self._last_full)
        if self.longterm and self.current_user:
            self.longterm.note_turn(self.current_user, "user", user_text)
            self.longterm.note_turn(self.current_user, "assistant", self._last_full)
            if self.longterm.due_for_update(self.current_user, self.longterm_update_every):
                # refresh the viewer's profile in the background (never blocks speaking)
                threading.Thread(target=self._update_profile,
                                 args=(self.current_user,), daemon=True).start()

    def perform_stream(self, directive: str,
                       max_tokens: int | None = None) -> Iterator[str]:
        """Act on an internal stage direction; remembers only Elysia's line."""
        yield from self._stream_clean(self._compose(directive), max_tokens=max_tokens)
        self.memory.add("assistant", self._last_full)

    # ------------------------------------------------------------------
    def _update_profile(self, user: str) -> None:
        """Fold the recent chat with this viewer into their durable profile (LLM)."""
        if not self.longterm:
            return
        p = self.longterm.profile(user) or {}
        recent = self.longterm.recent_turns(user)
        if not recent:
            return
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent[-12:])
        prior = (f"name: {p.get('name') or 'unknown'}\n"
                 f"summary: {p.get('summary') or '(none)'}\n"
                 f"facts: {'; '.join(p.get('facts') or []) or '(none)'}")
        prompt = (
            "You quietly maintain Elysia's private memory of one viewer. Update it from the "
            "recent chat below. Keep only durable, useful things (their name if they revealed "
            "it, stable preferences/interests, recurring topics, important life facts) — ignore "
            "small talk and one-off remarks. Be concise. Respond with ONLY compact JSON of the "
            'form {"name": <string or null>, "summary": <one short sentence>, "facts": '
            "[<short strings>]}. Do not add any other text.\n\n"
            f"Current memory:\n{prior}\n\nRecent chat:\n{convo}\n\nUpdated JSON:")
        try:
            out = "".join(self.provider.stream_generate(
                [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=240))
            data = _extract_json(_strip_think(out))
            if data:
                self.longterm.set_profile(
                    user, name=data.get("name"),
                    summary=data.get("summary"), facts=data.get("facts"))
                # refresh the recalled line so the next turn uses the updated profile
                if user == self.current_user:
                    self._recall = self.longterm.recall_text(user)
        except Exception:
            pass

    def reply(self, user_text: str) -> str:
        return "".join(self.reply_stream(user_text)).strip()
