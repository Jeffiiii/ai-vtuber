"""Stage 2 voice tests — run WITHOUT any voice packages installed.

They check the pure logic (language detection, factory wiring, graceful
unavailability) so `pytest` stays green even before you install the extras.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aivtuber.tts import create_tts, detect_lang          # noqa: E402
from aivtuber.tts.edge_tts_backend import EdgeTTSBackend   # noqa: E402
from aivtuber.stt import create_stt                        # noqa: E402


def test_detect_lang():
    assert detect_lang("hello there") == "en"
    assert detect_lang("你好呀") == "zh"
    assert detect_lang("good morning") == "en"
    assert detect_lang("早上好") == "zh"


def test_tts_factory_default_is_edge():
    tts = create_tts({})  # empty config -> defaults
    assert tts.name == "edge-tts"
    assert tts.output_ext == ".mp3"


def test_tts_factory_xtts():
    tts = create_tts({"tts_backend": "xtts"})
    assert tts.name == "xtts"
    assert tts.output_ext == ".wav"


def test_edge_voice_selection_by_language():
    b = EdgeTTSBackend(voice_en="EN_VOICE", voice_zh="ZH_VOICE")
    assert b._voice_for("hello") == "EN_VOICE"
    assert b._voice_for("你好") == "ZH_VOICE"


def test_backends_report_unavailable_gracefully_without_deps():
    # In a clean env the packages aren't installed; is_available must return a
    # (bool, str) tuple and never raise.
    ok, msg = create_tts({}).is_available()
    assert isinstance(ok, bool) and isinstance(msg, str)
    ok2, msg2 = create_stt({}).is_available()
    assert isinstance(ok2, bool) and isinstance(msg2, str)


def test_unknown_backends_raise():
    import pytest
    with pytest.raises(ValueError):
        create_tts({"tts_backend": "nope"})
    with pytest.raises(ValueError):
        create_stt({"stt_backend": "nope"})
