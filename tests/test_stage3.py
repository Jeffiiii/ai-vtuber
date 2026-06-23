"""Stage 3 tests — run WITHOUT twitchio / websocket-client / VTube Studio."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aivtuber.emotion import detect_emotion, expression_hotkey   # noqa: E402
from aivtuber.chat import create_chat_source, ChatMessage        # noqa: E402
from aivtuber.avatar import create_avatar, NullAvatar            # noqa: E402


def test_detect_emotion_basic():
    assert detect_emotion("Hehe, you noticed? ♪") == "playful"
    assert detect_emotion("Oh, sweetie... I'm sorry") == "sad"
    assert detect_emotion("Welcome, dear! Thank you so much") == "happy"
    assert detect_emotion("哎呀，你来啦") == "surprised"
    assert detect_emotion("The configuration is set to 4096.") == "neutral"


def test_expression_hotkey_mapping():
    mapping = {"happy": "Happy", "sad": "Sad"}
    assert expression_hotkey("happy", mapping) == "Happy"
    assert expression_hotkey("playful", mapping) is None


def test_chat_factory_console_and_queue():
    src = create_chat_source({})  # defaults to console
    assert src.name == "console"
    ok, _ = src.is_available()
    assert ok
    # queue plumbing works without starting the stdin thread
    src._q.put(ChatMessage(user="bob", text="hi", platform="console"))
    drained = src.drain()
    assert len(drained) == 1 and drained[0].text == "hi"


def test_avatar_factory_null_default():
    av = create_avatar({})
    assert isinstance(av, NullAvatar)
    ok, _ = av.connect()
    assert ok
    av.set_emotion("happy")  # must not raise


def test_unknown_backends_raise():
    import pytest
    with pytest.raises(ValueError):
        create_chat_source({"chat_source": "nope"})
    with pytest.raises(ValueError):
        create_avatar({"avatar_backend": "nope"})
