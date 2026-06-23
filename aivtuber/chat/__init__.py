"""Live chat ingestion (Stage 3). Sources: console (testing), Twitch."""

from .base import ChatMessage, ChatSource
from .factory import create_chat_source

__all__ = ["ChatMessage", "ChatSource", "create_chat_source"]
