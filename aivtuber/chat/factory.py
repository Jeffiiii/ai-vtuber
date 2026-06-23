"""Chat source factory."""

from __future__ import annotations

from .base import ChatSource


def create_chat_source(config: dict) -> ChatSource:
    name = (config.get("chat_source") or "console").lower()

    if name == "console":
        from .console_source import ConsoleChatSource
        return ConsoleChatSource()

    if name == "twitch":
        from .twitch_source import TwitchChatSource
        return TwitchChatSource(
            token=config.get("twitch_token", ""),
            channel=config.get("twitch_channel", ""),
        )

    if name in ("bilibili", "bili"):
        from .bilibili_source import BilibiliChatSource
        return BilibiliChatSource(room_id=config.get("bilibili_room_id", 0))

    raise ValueError(f"Unknown chat_source: {name!r}. Use 'console', 'twitch', or 'bilibili'.")
