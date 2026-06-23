"""Twitch chat source via twitchio. Install: pip install twitchio

You need a Twitch OAuth token (chat scope). Easiest: generate one at
https://twitchtokengenerator.com (or https://twitchapps.com/tmi) and put it in
config as `twitch_token` (format "oauth:xxxxx"), with `twitch_channel` = your
channel name.

Runs the twitchio client in a background thread and pushes messages into the queue.
"""

from __future__ import annotations

import asyncio
import threading

from .base import ChatMessage, ChatSource


class TwitchChatSource(ChatSource):
    def __init__(self, token: str, channel: str):
        super().__init__()
        self._token = token
        self._channel = channel
        self._thread = None

    def start(self) -> None:
        import twitchio  # lazy

        q = self._q
        channel = self._channel

        class _Bot(twitchio.Client):
            def __init__(self):
                super().__init__(token=token_value, initial_channels=[channel])

            async def event_message(self, message):
                if getattr(message, "echo", False):
                    return
                author = getattr(message.author, "name", "viewer") if message.author else "viewer"
                q.put(ChatMessage(user=author, text=message.content, platform="twitch"))

        token_value = self._token

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bot = _Bot()
            loop.run_until_complete(bot.start())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def is_available(self) -> tuple[bool, str]:
        try:
            import twitchio  # noqa: F401
        except ImportError:
            return False, "twitchio not installed. Run: pip install twitchio"
        if not self._token or not self._channel:
            return False, "Set twitch_token and twitch_channel in config.json"
        return True, f"Twitch ready (#{self._channel})"

    @property
    def name(self) -> str:
        return "twitch"
