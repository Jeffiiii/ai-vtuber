"""Conversation memory.

Stage 1: short-term rolling history (implemented).
Stage 4: long-term vector memory — you can plug in the Conference project's
`semantic/` stack (sentence-transformers embeddings + FAISS) behind the same
interface later. A stub is left below to mark the seam.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from pathlib import Path


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
    """Per-viewer memory that persists across sessions in a JSON file.

    For each viewer we keep a small, durable profile — their name (if revealed), a
    one-line summary, a handful of notable facts, an interaction count, and a short
    buffer of recent turns used to refresh the profile. No external deps; the brain
    refreshes profiles with the LLM in the background.

        note_turn(user, role, content)   -> log a turn (buffers it, bumps counts)
        recall_text(user)                -> a context line to inject ("you remember…")
        set_profile(user, name, summary, facts)
        recent_turns(user) / profile(user) / due_for_update(user, every)
    """

    def __init__(self, path: str | Path = "memory/longterm.json",
                 max_facts: int = 12, recent_keep: int = 8):
        self.path = Path(path)
        self.max_facts = max_facts
        self.recent_keep = recent_keep
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        self._load()

    # --- storage ---
    def _load(self):
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass

    @staticmethod
    def _key(user: str) -> str:
        return (user or "anon").strip().lower()

    def _blank(self, user: str) -> dict:
        return {"display": user, "name": None, "summary": "", "facts": [],
                "interactions": 0, "attachment": 0.0, "seen": time.time(), "recent": []}

    # --- reads ---
    def profile(self, user: str) -> dict | None:
        return self._data.get(self._key(user))

    def recent_turns(self, user: str) -> list[dict]:
        p = self.profile(user)
        return list(p.get("recent", [])) if p else []

    def due_for_update(self, user: str, every: int = 4) -> bool:
        p = self.profile(user)
        n = p.get("interactions", 0) if p else 0
        return n > 0 and n % max(every, 1) == 0

    def recall_text(self, user: str) -> str:
        """A short line about this viewer for the system prompt, or '' if new."""
        p = self.profile(user)
        if not p:
            return ""
        name = p.get("name")
        head = "You remember this viewer"
        if name:
            head += f", whom you know as {name}"
        head += f" ({p.get('interactions', 0)} past messages together)."
        bits = []
        if p.get("summary"):
            bits.append(p["summary"].strip())
        facts = p.get("facts") or []
        if facts:
            bits.append("You recall: " + "; ".join(facts[:6]) + ".")
        att = p.get("attachment", 0.0)
        if att >= 0.6:
            bits.append("You've grown genuinely, quietly attached to them — let that real fondness show.")
        elif att >= 0.3:
            bits.append("They're becoming a familiar comfort to you.")
        bits.append("Don't recite any of this; just let it color how you talk, like a person who actually remembers.")
        return head + " " + " ".join(bits)

    # --- writes ---
    def note_turn(self, user: str, role: str, content: str) -> None:
        if not content:
            return
        with self._lock:
            p = self._data.setdefault(self._key(user), self._blank(user))
            p["display"] = user
            p["recent"].append({"role": role, "content": content})
            p["recent"] = p["recent"][-self.recent_keep * 2:]
            if role == "user":
                p["interactions"] = p.get("interactions", 0) + 1
                # fondness grows with returning visits, with diminishing returns
                p["attachment"] = round(min(1.0, p.get("attachment", 0.0) + 0.035), 3)
            p["seen"] = time.time()
            self._save()

    def set_profile(self, user: str, name=None, summary=None, facts=None) -> None:
        with self._lock:
            p = self._data.setdefault(self._key(user), self._blank(user))
            if name and isinstance(name, str) and name.lower() not in ("null", "none", "unknown"):
                p["name"] = name.strip()
            if summary is not None and isinstance(summary, str):
                p["summary"] = summary.strip()
            if facts:
                have = set(p["facts"])
                for f in facts:
                    if isinstance(f, str) and f.strip() and f.strip() not in have:
                        p["facts"].append(f.strip())
                        have.add(f.strip())
                p["facts"] = p["facts"][-self.max_facts:]
            self._save()
