"""Tests that run WITHOUT Ollama (provider is faked)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aivtuber.brain import Brain                      # noqa: E402
from aivtuber.llm.base import LLMProvider             # noqa: E402
from aivtuber.memory import ShortTermMemory           # noqa: E402
from aivtuber.persona import Persona                  # noqa: E402

# Use any persona that ships in the repo; pick the first that actually opens so the
# suite doesn't break when persona files are added/removed.
_PERSONA_DIR = Path(__file__).resolve().parent.parent / "persona"


def _first_readable_persona():
    for name in ("elysia.json", "cyrene.json", "default.json"):
        try:
            data = json.loads((_PERSONA_DIR / name).read_text(encoding="utf-8"))
            return _PERSONA_DIR / name, data["name"]
        except (FileNotFoundError, OSError, KeyError, json.JSONDecodeError):
            continue
    raise FileNotFoundError(f"No readable persona JSON in {_PERSONA_DIR}")


PERSONA_PATH, PERSONA_NAME = _first_readable_persona()


class FakeProvider(LLMProvider):
    """Echoes a canned reply; records the messages it was given."""

    def __init__(self, reply="hi there!"):
        self.reply = reply
        self.last_messages = None

    def generate(self, messages, temperature=0.8, max_tokens=512):
        self.last_messages = messages
        return self.reply

    def health_check(self):
        return True, "fake ok"

    @property
    def provider_name(self): return "Fake"

    @property
    def is_local(self): return True

    @property
    def model_name(self): return "fake-model"


def test_persona_loads_and_builds_prompt():
    p = Persona.load(PERSONA_PATH)
    sp = p.system_prompt()
    assert p.name == PERSONA_NAME
    assert PERSONA_NAME in sp
    # bilingual rule must be present so the model replies in the user's language
    assert "中文" in sp or "Chinese" in sp
    assert "Boundaries" in sp


def test_persona_examples_alternate_roles():
    p = Persona.load(PERSONA_PATH)
    msgs = p.example_messages()
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_brain_injects_system_examples_and_history():
    p = Persona.load(PERSONA_PATH)
    fake = FakeProvider("hey!")
    brain = Brain(fake, p, memory=ShortTermMemory(max_turns=4))

    out = brain.reply("hello")
    assert out == "hey!"

    msgs = fake.last_messages
    assert msgs[0]["role"] == "system"            # system prompt first
    assert any(m["role"] == "assistant" for m in msgs)  # few-shot examples present
    assert msgs[-1] == {"role": "user", "content": "hello"}  # current turn last


def test_memory_persists_across_turns():
    p = Persona.load(PERSONA_PATH)
    fake = FakeProvider("ok")
    brain = Brain(fake, p, memory=ShortTermMemory(max_turns=4))
    brain.reply("first")
    brain.reply("second")
    # on the 2nd call, the 1st exchange should be in history
    contents = [m["content"] for m in fake.last_messages]
    assert "first" in contents
    assert "ok" in contents


def test_memory_window_caps():
    mem = ShortTermMemory(max_turns=2)  # keeps 2 turns = 4 messages
    for i in range(10):
        mem.add("user", f"m{i}")
    assert len(mem.messages()) == 4


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
