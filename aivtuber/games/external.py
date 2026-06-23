"""External game agent (scaffold) — control a real game via screen + keypresses.

This is the framework Neuro-style game-playing uses: SEE the screen, DECIDE an
action, ACT with key presses. Real games need per-game tuning (what to look for,
which keys), so this ships as a safe, generic skeleton:

  * 'sees' via a ScreenDescriber (OCR now; swap to a VLM later)
  * asks the brain to pick ONE action from a fixed vocabulary
  * 'acts' by pressing the mapped key (pyautogui) — DRY-RUN by default (prints only)

Install to actually press keys: pip install pyautogui
Keep dry_run=True until you trust it; auto-pressing keys can do anything on your PC.
"""

from __future__ import annotations

import re

from .base import GameAgent


class ExternalGameAgent(GameAgent):
    def __init__(self, describer=None, actions: dict | None = None,
                 dry_run: bool = True, max_steps: int = 50):
        # actions: {action_name: key}, e.g. {"left":"a","right":"d","jump":"space"}
        self.describer = describer
        self.actions = actions or {"left": "a", "right": "d", "jump": "space", "wait": ""}
        self.dry_run = dry_run
        self.max_steps = max_steps
        self._steps = 0
        self._last_seen = ""

    @property
    def name(self) -> str:
        return "external"

    def intro(self) -> str:
        verbs = ", ".join(self.actions)
        mode = "DRY-RUN (no real keys)" if self.dry_run else "LIVE (pressing keys!)"
        return f"Playing an external game [{mode}]. Possible actions: {verbs}."

    def move_prompt(self) -> str:
        if self.describer is not None:
            try:
                self._last_seen = self.describer.describe()
            except Exception:
                self._last_seen = ""
        seen = self._last_seen or "(nothing readable on screen)"
        verbs = ", ".join(self.actions)
        return (f"You are playing a game. On screen you can see: \"{seen}\". "
                f"Choose exactly ONE action from [{verbs}] and say it, with a short "
                f"in-character reaction. State the action word clearly.")

    def _parse_action(self, text: str) -> str | None:
        low = (text or "").lower()
        for action in self.actions:
            if re.search(rf"\b{re.escape(action)}\b", low):
                return action
        return None

    def apply(self, reply_text: str) -> str:
        self._steps += 1
        action = self._parse_action(reply_text)
        if action is None:
            return "(no clear action — waiting)"
        key = self.actions.get(action, "")
        if not key:
            return f"Elysia chooses to wait."
        if self.dry_run:
            return f"Elysia → {action}  (dry-run: would press '{key}')"
        try:
            import pyautogui
            pyautogui.press(key)
            return f"Elysia → {action}  (pressed '{key}')"
        except Exception as e:
            return f"Elysia → {action}  (couldn't press '{key}': {e})"

    def is_over(self) -> bool:
        return self._steps >= self.max_steps

    def result_text(self) -> str:
        return f"Stopped after {self._steps} steps. (Stop anytime with Ctrl+C.)"
