"""Game-agent interface (Stage 4 — hands).

A GameAgent lets Elysia *take actions toward a goal*, not just chat. The loop:

    print(agent.intro())
    while not agent.is_over():
        directive = agent.move_prompt()          # describe state + ask for a move
        reply = brain.perform_stream(directive)  # she thinks/acts in character
        print(agent.apply(reply))                # parse her move, advance, narrate
    print(agent.result_text())

Agents keep their own state and parse the model's free-text reply into a concrete
move (robust to her chatty style). Built-ins (tic-tac-toe, guessing) run fully with
the text model; ExternalGameAgent scaffolds real game control.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


def first_int(text: str, lo: int, hi: int) -> int | None:
    """Pull the first integer in [lo, hi] from free text (she may ramble)."""
    for m in re.findall(r"-?\d+", text or ""):
        try:
            v = int(m)
        except ValueError:
            continue
        if lo <= v <= hi:
            return v
    return None


class GameAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def intro(self) -> str: ...

    @abstractmethod
    def move_prompt(self) -> str:
        """A stage-direction telling Elysia the current state and to make her move,
        in character, clearly stating the move (e.g. a number)."""
        ...

    @abstractmethod
    def apply(self, reply_text: str) -> str:
        """Parse her move from `reply_text`, advance the game, return a narration."""
        ...

    @abstractmethod
    def is_over(self) -> bool: ...

    @abstractmethod
    def result_text(self) -> str: ...
