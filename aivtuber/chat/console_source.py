"""Console chat source — type messages to simulate viewers.

Lets you test the full live loop (chat -> brain -> voice -> avatar) with no
platform account. Runs a background thread reading stdin.
"""

from __future__ import annotations

import threading

from .base import ChatMessage, ChatSource


class ConsoleChatSource(ChatSource):
    def __init__(self, user: str = "tester"):
        super().__init__()
        self._user = user
        self._stop = False

    def _loop(self):
        while not self._stop:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                break
            line = line.strip()
            if line:
                self._q.put(ChatMessage(user=self._user, text=line, platform="console"))

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._stop = True

    def is_available(self) -> tuple[bool, str]:
        return True, "console chat ready (type to simulate viewers)"

    @property
    def name(self) -> str:
        return "console"
