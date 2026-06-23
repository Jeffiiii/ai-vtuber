"""Director tests — dep-free, no Ollama. Uses a fake brain + controllable clock."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aivtuber.director import Director, Mood   # noqa: E402


class FakeBrain:
    """Records what it was asked to do; returns a one-piece stream."""

    def __init__(self):
        self.max_tokens = 400
        self.note = None
        self.calls = []  # ("reply"|"perform", text)

    def set_note(self, note):
        self.note = note

    def reply_stream(self, user_text):
        self.calls.append(("reply", user_text))
        yield "ok"

    def perform_stream(self, directive, max_tokens=None):
        self.calls.append(("perform", directive))
        yield "ok"


class FakeClock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
    def advance(self, dt): self.t += dt


def _director(idle=8.0):
    clock = FakeClock()
    d = Director(FakeBrain(), idle_seconds=idle, rng=random.Random(0), clock=clock)
    return d, clock


def test_silent_when_quiet_and_not_idle():
    d, clock = _director(idle=8.0)
    assert d.decide() is None          # just started, not idle yet
    action, stream = d.step()
    assert action is None and stream is None


def test_responds_to_viewer_first():
    d, clock = _director()
    d.add_viewer("bob", "hi elysia")
    action, stream = d.step()
    assert action == "respond"
    assert "".join(stream) == "ok"
    assert d.brain.calls[-1] == ("reply", "bob: hi elysia")


def test_event_takes_priority_over_viewer():
    d, clock = _director()
    d.add_viewer("bob", "hi")
    d.add_event("followed")
    action, stream = d.step()
    assert action == "event"
    assert "".join(stream) == "ok"     # consume the lazy stream so the brain runs
    assert d.brain.calls[-1][0] == "perform"
    assert "followed" in d.brain.calls[-1][1]


def test_speaks_unprompted_after_idle():
    d, clock = _director(idle=8.0)
    clock.advance(9.0)                  # now past the idle threshold
    action, stream = d.step()
    assert action in ("initiate", "ask", "continue", "muse")
    assert "".join(stream) == "ok"
    assert d.brain.calls[-1][0] == "perform"


def test_mood_note_is_set_before_speaking():
    d, clock = _director()
    d.add_viewer("bob", "hi")
    d.step()
    assert d.brain.note  # a mood note (Chinese by default) was injected


def test_autonomous_directive_language_is_chinese_by_default():
    d, clock = _director()
    clock.advance(9.0)
    action, stream = d.step()
    assert "".join(stream) == "ok"
    kind, directive = d.brain.calls[-1]
    assert kind == "perform"
    assert any("一" <= ch <= "鿿" for ch in directive)  # contains Chinese


def test_mood_label_buckets():
    assert Mood(energy=0.9).label == "bubbly and hyper"
    assert Mood(energy=0.1).label == "quiet and dreamy"
    m = Mood(energy=0.5, rng=random.Random(0))
    m.drift()                           # must stay in range
    assert 0.0 <= m.energy <= 1.0
