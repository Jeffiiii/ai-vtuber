"""Autonomous mode (Stage 4) — Elysia as a living character, not a chatbot.

She talks on her own: when chat is quiet she starts topics, asks questions,
continues threads, and muses — driven by the Director on a timer. Viewer messages
and events interrupt with priority.

    python -m aivtuber.autonomous              # console chat, prints (test the feel)
    python -m aivtuber.autonomous --twitch     # read Twitch chat
    python -m aivtuber.autonomous --avatar     # drive VTube Studio
    python -m aivtuber.autonomous --no-speak   # text only

Type messages to act as a viewer; press Enter on an empty line does nothing.
Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

from .brain import Brain
from .config import load_config
from .director import Director, Mood
from .emotion import detect_emotion
from .llm import create_provider
from .memory import ShortTermMemory
from .persona import Persona


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run Elysia in autonomous (alive) mode")
    ap.add_argument("--twitch", action="store_true")
    ap.add_argument("--avatar", action="store_true")
    ap.add_argument("--no-speak", action="store_true")
    ap.add_argument("--idle", type=float, default=None,
                    help="Seconds of quiet before she speaks on her own")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.json")
    persona = Persona.load(root / cfg["persona_path"])
    provider = create_provider(cfg)

    print(f"\n=== {persona.name} — AUTONOMOUS ===")
    ok, status = provider.health_check()
    print(f"  LLM: {provider.provider_name}/{provider.model_name} — {status}")
    if not ok:
        print("  ✗ Start Ollama first."); return 1
    provider.ensure_ready()

    # chat
    cfg_chat = dict(cfg, chat_source="twitch" if args.twitch else "console")
    from .chat import create_chat_source
    chat = create_chat_source(cfg_chat)
    cok, cmsg = chat.is_available()
    print(f"  Chat: {chat.name} — {cmsg}")
    if not cok:
        print("  ✗ Chat source not ready."); return 1

    # avatar
    cfg_av = dict(cfg, avatar_backend="vtube-studio" if args.avatar else "null")
    from .avatar import create_avatar
    avatar = create_avatar(cfg_av)
    _aok, amsg = avatar.connect()
    print(f"  Avatar: {avatar.name} — {amsg}")

    # voice
    speak = not args.no_speak
    tts = None
    if speak:
        from .tts import create_tts
        tts = create_tts(cfg)
        tok, tmsg = tts.is_available()
        print(f"  Voice: {tts.name} — {tmsg}")
        speak = tok

    brain = Brain(provider, persona,
                  memory=ShortTermMemory(max_turns=int(cfg["max_turns"])),
                  temperature=float(cfg["temperature"]),
                  max_tokens=int(cfg["max_tokens"]),
                  max_examples=int(cfg.get("max_examples", 8)))

    director = Director(
        brain,
        idle_seconds=float(args.idle if args.idle is not None
                           else cfg.get("director_idle_seconds", 8.0)),
        mood=Mood(energy=float(cfg.get("director_start_energy", 0.6))),
        language=cfg.get("director_language", "zh"),
    )

    chat.start()
    tick = float(cfg.get("director_tick_seconds", 1.0))
    print(f"  Alive. She'll speak on her own after ~{director.idle_seconds:.0f}s of "
          f"quiet. (Ctrl+C to stop)\n")

    def emit(action: str, stream) -> None:
        tag = "" if action == "respond" else f"  ({action})"
        print(f"{persona.name}{tag} > ", end="", flush=True)
        chunks = []
        for piece in stream:
            print(piece, end="", flush=True)
            chunks.append(piece)
        print("\n")
        reply = "".join(chunks).strip()
        try:
            avatar.set_emotion(detect_emotion(reply))
        except Exception:
            pass
        if speak and tts and reply:
            try:
                out = tempfile.mktemp(suffix=tts.output_ext)
                from . import audio
                audio.play(tts.synthesize(reply, out))
            except Exception as e:
                print(f"[tts error: {e}]")

    running = True
    try:
        while running:
            for m in chat.drain():
                cmd = m.text.strip().lower()
                if cmd in ("/quit", "/exit"):
                    running = False
                    break
                if cmd == "/reset":
                    brain.memory.clear()
                    print("(memory cleared)\n")
                    continue
                print(f"[{m.platform}] {m.user}: {m.text}")
                director.add_viewer(m.user, m.text)
            if not running:
                break
            action, stream = director.step()
            if stream is not None:
                try:
                    emit(action, stream)
                except Exception as e:
                    print(f"\n[error: {e}]\n")
            else:
                time.sleep(tick)
    except KeyboardInterrupt:
        print("\nGoing offline. Bye!")
    finally:
        chat.stop()
        avatar.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
