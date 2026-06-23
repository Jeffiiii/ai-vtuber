"""Number-guessing game — Elysia guesses a secret number; the agent gives feedback.

A clean demo of goal-directed 'hands': she takes actions (guesses), gets feedback
(higher/lower), and converges. Fully self-running with the text model.
"""

from __future__ import annotations

import random

from .base import GameAgent, first_int


class GuessingGame(GameAgent):
    def __init__(self, lo: int = 1, hi: int = 100, rng: random.Random | None = None):
        self.lo, self.hi = lo, hi
        self._rng = rng or random.Random()
        self._secret = self._rng.randint(lo, hi)
        self._last = None          # her last guess
        self._feedback = "no guesses yet"
        self._tries = 0
        self._won = False

    @property
    def name(self) -> str:
        return "guessing"

    def intro(self) -> str:
        return (f"Let's play a guessing game! I'm thinking of a number between "
                f"{self.lo} and {self.hi}, and Elysia will try to find it.")

    def move_prompt(self) -> str:
        return (f"You are playing a guessing game. The number is between {self.lo} and "
                f"{self.hi}. Feedback so far: {self._feedback}. In character, make your "
                f"next guess and clearly say the number.")

    def apply(self, reply_text: str) -> str:
        guess = first_int(reply_text, self.lo, self.hi)
        if guess is None:
            return "(couldn't read a number from that — she'll try again)"
        self._tries += 1
        self._last = guess
        if guess == self._secret:
            self._won = True
            self._feedback = f"{guess} is correct!"
            return f"🎉 {guess} is exactly right! ({self._tries} tries)"
        if guess < self._secret:
            self._feedback = f"{guess} is too LOW"
            return f"{guess} — too low. Higher!"
        self._feedback = f"{guess} is too HIGH"
        return f"{guess} — too high. Lower!"

    def is_over(self) -> bool:
        return self._won or self._tries >= 12

    def result_text(self) -> str:
        if self._won:
            return f"She found it ({self._secret}) in {self._tries} tries — well done, Elysia!"
        return f"Out of tries! The number was {self._secret}."
