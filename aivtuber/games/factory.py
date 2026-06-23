"""Game-agent factory."""

from __future__ import annotations

from .base import GameAgent


def create_game(name: str, config: dict | None = None) -> GameAgent:
    config = config or {}
    name = (name or "guessing").lower()

    if name in ("guess", "guessing"):
        from .guessing import GuessingGame
        return GuessingGame(lo=int(config.get("guess_lo", 1)),
                            hi=int(config.get("guess_hi", 100)))

    if name in ("ttt", "tictactoe", "tic-tac-toe"):
        from .tictactoe import TicTacToe
        return TicTacToe()

    if name in ("external", "game"):
        from .external import ExternalGameAgent
        describer = None
        if config.get("game_use_vision", True):
            try:
                from ..vision import create_vision
                describer = create_vision(config)
            except Exception:
                describer = None
        return ExternalGameAgent(
            describer=describer,
            actions=config.get("game_actions") or None,
            dry_run=bool(config.get("game_dry_run", True)),
            max_steps=int(config.get("game_max_steps", 50)),
        )

    raise ValueError(f"Unknown game: {name!r}. Use 'guessing', 'tictactoe', or 'external'.")
