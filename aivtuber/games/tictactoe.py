"""Tic-tac-toe — Elysia (O) vs a simple opponent (X, random by default).

Board cells are numbered 1-9:
    1 | 2 | 3
    4 | 5 | 6
    7 | 8 | 9
She picks a cell each turn; the agent parses it, plays it, then the opponent moves.
Self-running with the text model.
"""

from __future__ import annotations

import random

from .base import GameAgent, first_int

_WINS = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
         (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


class TicTacToe(GameAgent):
    def __init__(self, rng: random.Random | None = None):
        self.board = [" "] * 9      # indices 0-8
        self._rng = rng or random.Random()
        self._msg = ""

    @property
    def name(self) -> str:
        return "tictactoe"

    def intro(self) -> str:
        return "Tic-tac-toe time! I'm O, my challenger is X. Cells are numbered 1-9."

    def _render(self) -> str:
        b = self.board
        return (f"{b[0] or 1}|{b[1] or 2}|{b[2] or 3}  "
                f"{b[3] or 4}|{b[4] or 5}|{b[5] or 6}  "
                f"{b[6] or 7}|{b[7] or 8}|{b[8] or 9}")

    def _winner(self) -> str | None:
        for a, b, c in _WINS:
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if " " not in self.board:
            return "draw"
        return None

    def _free(self) -> list[int]:
        return [i for i, v in enumerate(self.board) if v == " "]

    def move_prompt(self) -> str:
        free = ", ".join(str(i + 1) for i in self._free())
        return (f"You're playing tic-tac-toe as O. Board (numbers = empty cells): "
                f"{self._render()}. Available cells: {free}. In character, pick ONE "
                f"empty cell and clearly say its number.")

    def apply(self, reply_text: str) -> str:
        cell = first_int(reply_text, 1, 9)
        if cell is None or self.board[cell - 1] != " ":
            # invalid/taken -> pick a random free cell so the game keeps moving
            choices = self._free()
            if not choices:
                return ""
            cell = self._rng.choice(choices) + 1
            note = f"(picked {cell} for her)"
        else:
            note = ""
        self.board[cell - 1] = "O"
        msg = f"Elysia plays O at {cell}. {note}".strip()
        if self._winner():
            return msg
        # opponent (random) responds
        free = self._free()
        if free:
            opp = self._rng.choice(free)
            self.board[opp] = "X"
            msg += f"  | X plays at {opp + 1}."
        return msg

    def is_over(self) -> bool:
        return self._winner() is not None

    def result_text(self) -> str:
        w = self._winner()
        if w == "O":
            return "Elysia (O) wins! ✨"
        if w == "X":
            return "X wins this time — rematch?"
        return "It's a draw! Good game."
