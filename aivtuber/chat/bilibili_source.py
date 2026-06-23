"""Bilibili live danmaku (弹幕) chat source.

Install: pip install bilibili-api-python

Set `bilibili_room_id` in config to your live room id. Reads danmaku in a background
thread and pushes them into the queue like any other ChatSource. Anonymous read of
public danmaku needs no login; some rooms/features may require credentials (add a
SESSDATA cookie later if needed).
"""

from __future__ import annotations

import asyncio
import threading

from .base import ChatMessage, ChatSource


class BilibiliChatSource(ChatSource):
    def __init__(self, room_id: int):
        super().__init__()
        self.room_id = int(room_id)
        self._thread = None

    def start(self) -> None:
        from bilibili_api import live, sync  # noqa: F401  (import check)
        from bilibili_api.live import LiveDanmaku

        q = self._q
        room_id = self.room_id

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            room = LiveDanmaku(room_id)

            @room.on("DANMU_MSG")
            async def _on_danmaku(event):
                try:
                    info = event["data"]["info"]
                    text = info[1]
                    user = info[2][1]
                except Exception:
                    return
                q.put(ChatMessage(user=str(user), text=str(text), platform="bilibili"))

            loop.run_until_complete(room.connect())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def is_available(self) -> tuple[bool, str]:
        try:
            import bilibili_api  # noqa: F401
        except ImportError:
            return False, "bilibili-api not installed. Run: pip install bilibili-api-python"
        if not self.room_id:
            return False, "Set bilibili_room_id in config.json"
        return True, f"Bilibili ready (room {self.room_id})"

    @property
    def name(self) -> str:
        return "bilibili"
