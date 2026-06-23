"""Live loop (Stage 3) — the VTuber going live.

Ties everything together:  chat in -> Brain -> emotion + voice out -> avatar.

    python -m aivtuber.live                 # console chat, null avatar (test the loop)
    python -m aivtuber.live --twitch        # read Twitch chat (needs config + twitchio)
    python -m aivtuber.live --avatar        # drive VTube Studio expressions

Start simple (console + null + voice), then turn on Twitch and the avatar once each
piece works. Everything degrades gracefully: if voice/avatar aren't installed, the
loop still runs and prints.

NOTE: this is a first, simple loop — it answers the most recent unanswered chat
message every few seconds. Barge-in, autonomous topic-picking, and smart message
selection are the next refinements (see STAGE3.md).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

from .brain import Brain
from .config import load_config
from .emotion import detect_emotion
from .llm import create_provider
from .memory import ShortTermMemory
from .persona import Persona


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the VTuber live loop")
    ap.add_argument("--twitch", action="store_true", help="Use Twitch chat (else console)")
    ap.add_argument("--avatar", action="store_true", help="Drive VTube Studio (else null)")
    ap.add_argument("--no-speak", action="store_true", help="Disable TTS")
    ap.add_argument("--interval", type=float, default=2.0,
                    help="Seconds between checking chat for a new message")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.json")
    persona = Persona.load(root / cfg["persona_path"])
    provider = create_provider(cfg)

    print(f"\n=== {persona.name} — LIVE ===")
    ok, status = provider.health_check()
    print(f"  LLM: {provider.provider_name}/{provider.model_name} — {status}")
    if not ok:
        print("  ✗ Start Ollama first."); return 1
    provider.ensure_ready()

    # chat source
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
    aok, amsg = avatar.connect()
    print(f"  Avatar: {avatar.name} — {amsg}")

    # voice (optional)
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

    chat.start()
    print("\n  LIVE. (Ctrl+C to stop)\n")

    try:
        while True:
            msgs = chat.drain()
            if not msgs:
                time.sleep(args.interval)
                continue
            # simplest policy: answer the most recent message
            msg = msgs[-1]
            print(f"[{msg.platform}] {msg.user}: {msg.text}")

            print(f"{persona.name} > ", end="", flush=True)
            chunks = []
            try:
                for piece in brain.reply_stream(f"{msg.user}: {msg.text}"):
                    print(piece, end="", flush=True)
                    chunks.append(piece)
                print("\n")
            except Exception as e:
                print(f"\n[brain error: {e}]\n")
                continue
            reply = "".join(chunks).strip()

            # emotion -> avatar
            try:
                avatar.set_emotion(detect_emotion(reply))
            except Exception:
                pass

            # voice
            if speak and tts and reply:
                try:
                    out = tempfile.mktemp(suffix=tts.output_ext)
                    from . import audio
                    audio.play(tts.synthesize(reply, out))
                except Exception as e:
                    print(f"[tts error: {e}]")
    except KeyboardInterrupt:
        print("\nGoing offline. Bye!")
    finally:
        chat.stop()
        avatar.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
