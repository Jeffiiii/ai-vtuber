"""Interactive terminal chat — the Stage 1 MVP you can run today.

    python -m aivtuber.cli

Type to chat. Commands: /reset (clear memory), /quit or /exit.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .brain import Brain
from .config import load_config
from .llm import create_provider
from .memory import ShortTermMemory
from .persona import Persona


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent.parent  # repo root
    cfg = load_config(root / "config.json")

    persona_path = root / cfg["persona_path"]
    persona = Persona.load(persona_path)

    provider = create_provider(cfg)

    print(f"\n=== {persona.name} — AI VTuber (Stage 1 text MVP) ===")
    ok, status = provider.health_check()
    print(f"  LLM: {provider.provider_name} / {provider.model_name}")
    print(f"  Status: {status}")
    if not ok:
        print("\n  ✗ Cannot reach a model yet. Install/start Ollama, then retry.")
        return 1

    print("  Warming up the model… (first run also downloads it)")
    ready, msg = provider.ensure_ready()
    if not ready:
        print(f"  ✗ {msg}")
        return 1
    print(f"  ✓ {msg}\n  Type to chat. /reset to clear, /quit to exit.\n")

    brain = Brain(provider, persona,
                  memory=ShortTermMemory(max_turns=int(cfg["max_turns"])),
                  temperature=float(cfg["temperature"]),
                  max_tokens=int(cfg["max_tokens"]),
                  max_examples=int(cfg.get("max_examples", 8)))
    print(f"  (persona has {persona.example_count()} examples; "
          f"priming with {brain.max_examples} per session)\n")

    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            return 0
        if not user:
            continue
        if user in ("/quit", "/exit"):
            print("bye!")
            return 0
        if user == "/reset":
            brain.memory.clear()
            print("(memory cleared)\n")
            continue

        print(f"{persona.name} > ", end="", flush=True)
        try:
            for piece in brain.reply_stream(user):
                print(piece, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\n[error: {e}]\n")


if __name__ == "__main__":
    sys.exit(main())
