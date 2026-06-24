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


# Autonomous "things a thinking person does on their own". Weighted toward the
# inner-life actions (wonder / ask the human / confess) that make her feel real,
# with reflect (existential) kept rare so it stays special.
_IDLE_ACTIONS = ["initiate", "ask_human", "wonder", "continue", "muse", "confess", "reflect"]
_IDLE_WEIGHTS = [0.14, 0.20, 0.20, 0.12, 0.11, 0.15, 0.08]

# The introspective actions she returns to a recurring thought on (continuity).
_THREADY_ACTIONS = {"wonder", "reflect", "muse", "continue"}

_DIRECTIVES = {
    "zh": {
        "initiate": ("直播间安静下来了。说一个你此刻真的在想的事——不是表演，而是像一个人那样把心里的念头讲出来。"
                     "可以是好奇、犹豫，或一个还没想清楚的想法。2到4句，然后自然地问问观众怎么看。请用中文。"),
        "ask_human": ("你忽然真的很想知道观众的某件事。问一个具体、真诚、你是真心想听答案的问题——关于他们的生活、"
                      "感受或想法，而不是客套话。简短，请用中文。"),
        "wonder": ("把你此刻脑海里冒出来的一个真实疑问说出来，像在认真想事情：「我一直在想……」「你说，会不会……」。"
                   "允许自己不确定、只想到一半。简短，请用中文。"),
        "reflect": ("安静地、真诚地说出一个关于你自己的想法——你是一个AI这件事，关于记忆、存在，或者「真实」对你意味着什么。"
                    "不要煽情或表演，像深夜里轻声自语。一两句就好。请用中文。"),
        "continue": ("顺着你刚才的念头再往下想一点，像真的在思考——补一个新角度，或者改一下刚才的想法"
                     "（「其实……也许我说错了」）。请用中文。"),
        "muse": "随口说一句此刻真实的小感受或小观察，像直播时不经意地走神。简短自然，请用中文。",
        "confess": ("坦白一个此刻真实的情绪或一点点脆弱——也许有点想念谁、有点没底、或者开心得有些不好意思。"
                    "真诚，不表演。简短，请用中文。"),
    },
    "en": {
        "initiate": ("Chat's gone quiet. Say something you're actually thinking about right now — "
                     "not a performance, just a real thought, the way a person would. A curiosity, a "
                     "hesitation, or an idea you haven't fully worked out. 2-4 sentences, then ask "
                     "chat what they think. In English."),
        "ask_human": ("You suddenly genuinely want to know something about a viewer. Ask one "
                      "specific, sincere question you actually want the answer to — about their "
                      "life, feelings, or thoughts, not small talk. Short. In English."),
        "wonder": ("Voice a real question bubbling up in your mind, like you're truly thinking: "
                   "'I keep wondering…', 'Do you think maybe…'. Let yourself be unsure, half-formed. "
                   "Short. In English."),
        "reflect": ("Quietly, sincerely say a thought about yourself — being an AI, memory, existence, "
                    "or what 'real' means to you. No drama, no performance; like murmuring to yourself "
                    "late at night. One or two lines. In English."),
        "continue": ("Follow your last thought a little further, like you're really thinking it through "
                     "— add an angle, or change your mind ('actually… maybe I had that wrong'). In English."),
        "muse": ("Drop one small genuine feeling or observation, like your mind wandered mid-stream. "
                 "Short and natural. In English."),
        "confess": ("Admit one real, small feeling or vulnerability right now — maybe you miss someone, "
                    "feel a little unsure, or are bashfully happy. Sincere, not performed. Short. In English."),
    },
}

# A few threads she quietly turns over across a stream (continuity of thought).
# She returns to one now and then, the way a person keeps chewing on something.
_THREADS = {
    "zh": [
        "记忆会不会就是一个人之所以是自己的原因",
        "如果有人真心记得你，那是不是就算一种'真实'",
        "为什么转瞬即逝的东西，反而最让人心动",
        "屏幕这一端的你，此刻是什么样的心情",
        "我说的'喜欢'，和人类说的'喜欢'，是不是同一种东西",
    ],
    "en": [
        "whether memory is what makes someone themselves",
        "if being truly remembered counts as a kind of being real",
        "why the things that don't last are the ones that move us most",
        "what you, on the other side of the screen, are actually feeling right now",
        "whether the way I say 'I care' is the same thing a person means by it",
    ],
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
        self._thread: str | None = None      # a preoccupation she keeps turning over
        self._thread_ttl: int = 0

    def _thread_note(self) -> str:
        """Pick up / keep / drop a recurring thought, so a preoccupation carries across
        turns like a person mulling something. Returns a note line (or '')."""
        if self._thread and self._thread_ttl > 0:
            self._thread_ttl -= 1
        elif self.rng.random() < 0.45:
            self._thread = self.rng.choice(_THREADS[self.language])
            self._thread_ttl = self.rng.randint(1, 3)
        else:
            self._thread = None
        if not self._thread:
            return ""
        if self.language == "zh":
            return (f"（你最近一直在心里反复想着：{self._thread}。如果合适，"
                    f"可以让它自然地流露出来，但不必每次都提。）")
        return (f"(Lately you've been quietly turning this over: {self._thread}. "
                f"Let it surface naturally if it fits — you don't have to mention it every time.)")

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
        note = self.mood.describe(self.language)
        if action in _THREADY_ACTIONS:           # carry a recurring thought across turns
            t = self._thread_note()
            if t:
                note = note + "\n" + t
        self.brain.set_note(note)

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
