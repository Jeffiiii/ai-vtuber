"""Audio playback helper (Windows-friendly, cross-platform fallbacks).

Plays the audio files produced by the TTS backends. Tries, in order:
  1) playsound (handles mp3 + wav, cross-platform)   -> pip install playsound==1.2.2
  2) winsound (Windows, WAV only)
  3) the OS default player (last resort)

Kept dependency-free at import time; everything is lazy.
"""

from __future__ import annotations

import os
import sys


def play(path: str) -> None:
    """Block until the audio file finishes playing. Best-effort across platforms."""
    # 1) playsound — best coverage (mp3 + wav)
    try:
        from playsound import playsound
        playsound(path)
        return
    except Exception:
        pass

    # 2) winsound — Windows, WAV only
    if sys.platform.startswith("win") and path.lower().endswith(".wav"):
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
            return
        except Exception:
            pass

    # 3) OS default player (non-blocking, last resort)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'afplay "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        print(f"[audio] Could not play {path}: {e}\n"
              f"[audio] Install a player: pip install playsound==1.2.2")
