"""Voice chat with Elysia (Stage 2) — she speaks her replies aloud.

    python -m aivtuber.voice_cli              # type to chat, hear replies
    python -m aivtuber.voice_cli --listen     # talk via microphone (push-to-talk)

Requires the voice extras:  pip install -r requirements-voice.txt
(TTS: edge-tts;  STT/--listen: faster-whisper + sounddevice + soundfile;
 playback: playsound==1.2.2)

The text app (`python -m aivtuber.cli`) still works with no extra installs — this
module is purely additive.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .brain import Brain
from .config import load_config
from .llm import create_provider
from .memory import ShortTermMemory
from .persona import Persona


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Voice chat with your VTuber")
    ap.add_argument("--listen", action="store_true", help="Use microphone input (STT)")
    ap.add_argument("--seconds", type=float, default=0.0,
                    help="With --listen: record a fixed N seconds instead of stop-on-silence")
    ap.add_argument("--no-speak", action="store_true", help="Disable TTS (text only)")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.json")
    persona = Persona.load(root / cfg["persona_path"])
    provider = create_provider(cfg)

    print(f"\n=== {persona.name} — voice mode ===")
    ok, status = provider.health_check()
    print(f"  LLM: {provider.provider_name}/{provider.model_name} — {status}")
    if not ok:
        print("  ✗ Start Ollama first."); return 1

    # ---- TTS setup ----
    speak = not args.no_speak
    tts = None
    if speak:
        from .tts import create_tts
        tts = create_tts(cfg)
        tok, msg = tts.is_available()
        print(f"  TTS: {tts.name} — {msg}")
        if not tok:
            print("  (continuing without voice; install extras to enable)")
            speak = False

    # ---- STT setup ----
    stt = None
    if args.listen:
        from .stt import create_stt
        from .stt import mic  # noqa: F401  (import check)
        stt = create_stt(cfg)
        sok, smsg = stt.is_available()
        print(f"  STT: {stt.name} — {smsg}")
        if not sok:
            print("  ✗ Install STT extras for --listen."); return 1

    provider.ensure_ready()
    brain = Brain(provider, persona,
                  memory=ShortTermMemory(max_turns=int(cfg["max_turns"])),
                  temperature=float(cfg["temperature"]),
                  max_tokens=int(cfg["max_tokens"]),
                  max_examples=int(cfg.get("max_examples", 8)))

    print("  Ready. /quit to exit, /reset to clear memory.\n")

    def get_user_input() -> str | None:
        if args.listen:
            input("(press Enter, then speak) ")
            from .stt import mic
            wav = (mic.record_fixed(args.seconds) if args.seconds > 0
                   else mic.record_until_silence())
            text = stt.transcribe(wav)
            print(f"you > {text}")
            return text
        try:
            return input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    while True:
        user = get_user_input()
        if user is None:
            print("\nbye!"); return 0
        if not user:
            continue
        if user in ("/quit", "/exit"):
            print("bye!"); return 0
        if user == "/reset":
            brain.memory.clear(); print("(memory cleared)\n"); continue

        print(f"{persona.name} > ", end="", flush=True)
        chunks = []
        try:
            for piece in brain.reply_stream(user):
                print(piece, end="", flush=True)
                chunks.append(piece)
            print("\n")
        except Exception as e:
            print(f"\n[error: {e}]\n"); continue

        if speak and tts:
            reply = "".join(chunks).strip()
            if reply:
                try:
                    out = tempfile.mktemp(suffix=tts.output_ext)
                    path = tts.synthesize(reply, out)
                    from . import audio
                    audio.play(path)
                except Exception as e:
                    print(f"[tts error: {e}]")

    # unreachable


if __name__ == "__main__":
    sys.exit(main())
