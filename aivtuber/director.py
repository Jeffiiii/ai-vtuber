"""The Director (Stage 4) — what turns Elysia from a chatbot into a character.

A chatbot is request -> response. A character is an agent that runs on a clock,
has a mood, and acts on its own. The Director decides, every tick, what Elysia
should do next:

  * respond   — answer a waiting viewer message (matches the VIEWER's language)
  * event     — react to a follow/sub/etc.
  * initiate  — when chat is quiet, bring up a new topic
  * ask       — ask the audience a question to get them talking
  * continue  — riff further on what she was just saying
  * muse      — a small spontaneous thought, like thinking aloud
  * (silent)  — sometimes the right move is to wait

Language policy: autonomous lines use the configured default language (Chinese by
default). Replies to viewers match the viewer's language (handled by the model).
So she stays in Chinese on her own and only switches to English when a viewer does.

Time is injected via `clock` so it's testable without real waiting.
"""

from __future__ import annotations

import random
import time
from collections import deque
from typing import Callable, Iterator

_LABELS_EN = {5: "bubbly and hyper", 4: "warm and playful", 3: "calm and gentle",
              2: "soft and a little sleepy", 1: "quiet and dreamy"}
_LABELS_ZH = {5: "活泼又兴奋", 4: "温暖又俏皮", 3: "平静又温柔",
              2: "柔软又有点困", 1: "安静又恍惚"}


class Mood:
    """A tiny evolving internal state. `energy` drifts; label is derived from it."""

    def __init__(self, energy: float = 0.6, rng: random.Random | None = None):
        self.energy = energy
        self._rng = rng or random.Random()

    def drift(self) -> None:
        self.energy += (0.6 - self.energy) * 0.1 + self._rng.uniform(-0.12, 0.12)
        self.energy = max(0.0, min(1.0, self.energy))

    def nudge(self, amount: float) -> None:
        self.energy = max(0.0, min(1.0, self.energy + amount))

    def _bucket(self) -> int:
        e = self.energy
        return 5 if e > 0.8 else 4 if e > 0.6 else 3 if e > 0.4 else 2 if e > 0.2 else 1

    @property
    def label(self) -> str:
        return _LABELS_EN[self._bucket()]

    def describe(self, language: str = "zh") -> str:
        if language == "zh":
            return f"（你现在的心情：{_LABELS_ZH[self._bucket()]}。让它体现在语气里，而不是直接说出来。）"
        return (f"(Right now your mood is {_LABELS_EN[self._bucket()]}. "
                f"Let it color your tone, not your words literally.)")


_IDLE_ACTIONS = ["initiate", "ask", "continue", "muse"]
_IDLE_WEIGHTS = [0.30, 0.25, 0.30, 0.15]

_DIRECTIVES = {
    "zh": {
        "initiate": "直播间安静下来了。主动聊一个你突然好奇或喜欢的小话题（一个想法、一段回忆，或一个俏皮的小看法），用你自己的语气，2到4句，然后邀请观众一起聊。请用中文。",
        "ask": "现在有点安静。向观众问一个有趣又具体的小问题，让大家开口聊天。保持角色感，简短而温柔。请用中文。",
        "continue": "顺着你刚才说的再聊一点——补一个新角度或俏皮的小插话，然后再把观众带回来。请用中文。",
        "muse": "随口说一句你此刻的小感想或小观察，像在直播时自言自语。简短又可爱。请用中文。",
    },
    "en": {
        "initiate": ("Chat has gone quiet. Bring up something you're suddenly curious or "
                     "excited about — a small thought, a memory, or a playful hot take — in "
                     "your own voice. 2 to 4 sentences, then invite chat to react. In English."),
        "ask": ("It's quiet. Ask your viewers a fun, specific question to get them talking. "
                "Stay in character, keep it short and inviting. In English."),
        "continue": ("Keep going on what you were just talking about — add a new angle or a "
                     "playful aside, then pull chat back in. In English."),
        "muse": ("Share one tiny spontaneous musing or observation, like thinking out loud "
                 "on stream. Short and charming. In English."),
    },
}

_EVENT_DIRECTIVE = {
    "zh": "有观众刚刚{ev}。请用中文，温柔又带着你的角色感回应，然后把气氛延续下去。",
    "en": "A viewer just {ev}. React warmly and in character, then keep the energy going.",
}

_OBSERVE_DIRECTIVE = {
    "zh": "你正在看屏幕，看到了：「{obs}」。请用中文，简短地、带着你的角色感对看到的内容做出反应或评论。",
    "en": "You're watching the screen and you see: \"{obs}\". React or comment on it briefly, in character.",
}


class Director:
    def __init__(self, brain, idle_seconds: float = 8.0,
                 mood: Mood | None = None,
                 rng: random.Random | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 language: str = "zh"):
        self.brain = brain
        self.idle_seconds = idle_seconds
        self.rng = rng or random.Random()
        self.mood = mood or Mood(rng=self.rng)
        self._clock = clock
        self.language = language if language in ("zh", "en") else "zh"
        self._last_activity = clock()
        self._pending: deque[tuple[str, str]] = deque()
        self._events: deque[str] = deque()
        self._observation: str | None = None

    # --- inputs ---
    def add_viewer(self, who: str, text: str) -> None:
        self._pending.append((who, text))

    def add_event(self, description: str) -> None:
        self._events.append(description)

    def add_observation(self, text: str) -> None:
        """Something Elysia 'sees' (from the vision module). She'll comment when free."""
        if text and text.strip():
            self._observation = text.strip()

    # --- decision ---
    def decide(self) -> str | None:
        if self._events:
            return "event"
        if self._pending:
            return "respond"
        if self._observation:
            return "observe"
        if self._clock() - self._last_activity >= self.idle_seconds:
            return self.rng.choices(_IDLE_ACTIONS, weights=_IDLE_WEIGHTS, k=1)[0]
        return None

    def step(self) -> tuple[str | None, Iterator[str] | None]:
        action = self.decide()
        if action is None:
            return None, None

        self.mood.drift()
        self.brain.set_note(self.mood.describe(self.language))

        if action == "respond":
            who, text = self._pending.popleft()
            self._last_activity = self._clock()
            # reply_stream lets the model match the VIEWER's language
            return "respond", self.brain.reply_stream(f"{who}: {text}")

        if action == "event":
            ev = self._events.popleft()
            self.mood.nudge(0.15)
            self._last_activity = self._clock()
            return "event", self.brain.perform_stream(
                _EVENT_DIRECTIVE[self.language].format(ev=ev))

        if action == "observe":
            obs = self._observation or ""
            self._observation = None
            self._last_activity = self._clock()
            return "observe", self.brain.perform_stream(
                _OBSERVE_DIRECTIVE[self.language].format(obs=obs))

        directive = _DIRECTIVES[self.language][action]
        self._last_activity = self._clock()
        return action, self.brain.perform_stream(directive)
