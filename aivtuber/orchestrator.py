"""Master orchestrator — the whole VTuber in one loop (Stage 4/5 capstone).

Combines everything that's been built:
  brain (fine-tuned)  ← LLM
  chat in             ← console / Twitch / Bilibili   (moderated)
  director            ← autonomy (talks on her own, mood, default Chinese)
  vision              ← optional screen 'sense' (OCR) → she comments on what she sees
  voice out           ← TTS (XTTS)        + avatar lip-sync
  ears (optional)     ← mic STT
  avatar              ← web face / VTube Studio
  moderation          ← screens viewer input AND her output
  games (optional)    ← she plays a game instead of free chat

Run examples:
    python -m aivtuber.orchestrator                          # console + web avatar + voice
    python -m aivtuber.orchestrator --platform bilibili      # read your Bilibili room
    python -m aivtuber.orchestrator --vision                 # comment on your screen
    python -m aivtuber.orchestrator --game tictactoe         # play a game
    python -m aivtuber.orchestrator --listen                 # talk to her by mic
    python -m aivtuber.orchestrator --no-voice --avatar null # quietest test

Everything degrades gracefully: missing extras just disable that feature. /quit ends it.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import moderation
from .brain import Brain
from .config import load_config
from .director import Director, Mood
from .emotion import detect_emotion
from .llm import create_provider
from .memory import ShortTermMemory
from .persona import Persona


def _run_game(brain, persona, game_name, cfg, speak, tts, avatar):
    """Play a game agent to completion, in character."""
    from .games import create_game
    agent = create_game(game_name, cfg)
    print(f"\n[game: {agent.name}] {agent.intro()}\n")
    from . import audio
    while not agent.is_over():
        directive = agent.move_prompt()
        chunks = []
        print(f"{persona.name} > ", end="", flush=True)
        for piece in brain.perform_stream(directive):
            print(piece, end="", flush=True)
            chunks.append(piece)
        print()
        reply = "".join(chunks).strip()
        allow, reply = moderation.filter_outgoing(reply)
        if speak and tts and reply:
            try:
                avatar.speak_start()
                audio.play(tts.synthesize(reply, tempfile.mktemp(suffix=tts.output_ext)))
            except Exception:
                pass
            finally:
                avatar.speak_end()
        print("  >> " + agent.apply(reply) + "\n")
        time.sleep(0.4)
    print(f"\n[game over] {agent.result_text()}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the full AI VTuber")
    ap.add_argument("--platform", default="console",
                    help="console | twitch | bilibili")
    ap.add_argument("--avatar", default="web", help="web | vtube-studio | null")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--listen", action="store_true", help="microphone input (STT)")
    ap.add_argument("--vision", action="store_true", help="comment on your screen (OCR)")
    ap.add_argument("--game", default="", help="play a game: guessing|tictactoe|external")
    ap.add_argument("--idle", type=float, default=None)
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.json")
    persona = Persona.load(root / cfg["persona_path"])
    provider = create_provider(cfg)

    print(f"\n=== {persona.name} — ORCHESTRATOR ===")
    ok, status = provider.health_check()
    print(f"  LLM: {provider.provider_name}/{provider.model_name} — {status}")
    if not ok:
        print("  ✗ Start the model server / Ollama first."); return 1
    provider.ensure_ready()

    brain = Brain(provider, persona,
                  memory=ShortTermMemory(max_turns=int(cfg["max_turns"])),
                  temperature=float(cfg["temperature"]),
                  max_tokens=int(cfg["max_tokens"]),
                  max_examples=int(cfg.get("max_examples", 8)))

    # --- voice ---
    speak = not args.no_voice
    tts = None
    if speak:
        from .tts import create_tts
        tts = create_tts(cfg)
        tok, tmsg = tts.is_available()
        print(f"  Voice: {tts.name} — {tmsg}")
        speak = tok
        # Load the model now so the slow first load happens at startup, not mid-stream
        # (XTTS only; edge-tts has no warmup). "LIVE" then means voice is truly ready.
        if speak and hasattr(tts, "warmup"):
            print("  Voice: warming up (loading model, first time can take a bit)…", flush=True)
            try:
                dev = tts.warmup()
                print(f"  Voice: ready on {dev}.")
            except Exception as e:
                print(f"  Voice: warmup failed ({e}); will load on first line.")

    # --- avatar ---
    from .avatar import create_avatar
    avatar = create_avatar(dict(cfg, avatar_backend=args.avatar))
    aok, amsg = avatar.connect()
    print(f"  Avatar: {avatar.name} — {amsg}")

    # --- game mode short-circuits the live loop ---
    if args.game:
        try:
            _run_game(brain, persona, args.game, cfg, speak, tts, avatar)
        except KeyboardInterrupt:
            print("\nstopped")
        finally:
            avatar.close()
        return 0

    # --- chat ---
    from .chat import create_chat_source
    chat = create_chat_source(dict(cfg, chat_source=args.platform))
    cok, cmsg = chat.is_available()
    print(f"  Chat: {chat.name} — {cmsg}")
    if not cok:
        print("  ✗ Chat source not ready."); return 1

    director = Director(
        brain,
        idle_seconds=float(args.idle if args.idle is not None
                           else cfg.get("director_idle_seconds", 8.0)),
        mood=Mood(energy=float(cfg.get("director_start_energy", 0.6))),
        language=cfg.get("director_language", "zh"),
    )

    # --- optional STT mic (push-to-talk in a thread) ---
    stt = None
    if args.listen:
        from .stt import create_stt
        stt = create_stt(cfg)
        sok, smsg = stt.is_available()
        print(f"  Ears: {stt.name} — {smsg}")
        if sok:
            def _mic_loop():
                from .stt import mic
                while True:
                    try:
                        wav = mic.record_until_silence()
                        text = stt.transcribe(wav)
                        if text.strip():
                            director.add_viewer("you (voice)", text.strip())
                    except Exception:
                        time.sleep(1)
            threading.Thread(target=_mic_loop, daemon=True).start()

    # --- optional vision watcher (thread) ---
    if args.vision:
        from .vision import create_vision
        describer = create_vision(cfg)
        vok, vmsg = describer.is_available()
        print(f"  Vision: {describer.name} — {vmsg}")
        if vok:
            interval = float(cfg.get("vision_interval_s", 20))
            def _vision_loop():
                last = ""
                while True:
                    try:
                        seen = describer.describe()
                        if seen and seen != last:
                            last = seen
                            director.add_observation(seen)
                    except Exception:
                        pass
                    time.sleep(interval)
            threading.Thread(target=_vision_loop, daemon=True).start()

    chat.start()
    tick = float(cfg.get("director_tick_seconds", 1.0))
    from . import audio
    print(f"\n  LIVE. She speaks on her own after ~{director.idle_seconds:.0f}s. "
          f"/quit to stop.\n")

    def emit(action, stream):
        tag = "" if action == "respond" else f"  ({action})"
        print(f"{persona.name}{tag} > ", end="", flush=True)
        chunks = []
        for piece in stream:
            print(piece, end="", flush=True)
            chunks.append(piece)
        print("\n")
        reply = "".join(chunks).strip()
        allow, reply = moderation.filter_outgoing(reply)
        if not allow:
            print(f"  [moderated] -> {reply}")
        try:
            avatar.set_emotion(detect_emotion(reply))
        except Exception:
            pass
        if speak and tts and reply:
            try:
                avatar.speak_start()
                audio.play(tts.synthesize(reply, tempfile.mktemp(suffix=tts.output_ext)))
            except Exception as e:
                print(f"[tts error: {e}]")
            finally:
                avatar.speak_end()

    running = True
    try:
        while running:
            for m in chat.drain():
                cmd = m.text.strip().lower()
                if cmd in ("/quit", "/exit"):
                    running = False
                    break
                if cmd == "/reset":
                    brain.memory.clear(); print("(memory cleared)\n"); continue
                allow, cleaned = moderation.filter_incoming(m.text)
                if not allow:
                    continue  # drop unsafe/empty viewer messages silently
                print(f"[{m.platform}] {m.user}: {cleaned}")
                director.add_viewer(m.user, cleaned)
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
