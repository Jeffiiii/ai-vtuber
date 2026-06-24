"""Standalone XTTS smoke test — finds exactly where voice stalls.

Run in the Windows app venv (the one with TTS installed), from the repo root:

    python scripts/tts_test.py

It prints a timestamp at every stage. Whichever stage it hangs on tells us the
cause: a long pause at "constructing TTS(...)" = the model manager is blocking on
a network call; a pause at "synthesizing" = compute; a pause after "wrote wav" =
audio playback. Paste me the output up to where it stops.
"""

import os
import sys
import time
from pathlib import Path

# Make the package importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stop any first-run network checks from hanging the load (we already have the model).
os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

_t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - _t0:6.1f}s] {msg}", flush=True)


def main() -> None:
    log("importing torch ...")
    import torch
    log(f"torch {torch.__version__}  cuda_available={torch.cuda.is_available()}")

    from aivtuber.tts.xtts_backend import _allow_xtts_unpickle
    _allow_xtts_unpickle(torch)
    log("unpickle patch applied")

    log("importing TTS ...")
    from TTS.api import TTS
    log("TTS imported")

    log("constructing TTS(xtts_v2)  <-- if it hangs HERE, it's the model manager / network")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    log("TTS constructed")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"moving model to {dev} ...")
    tts.to(dev)
    log("model on device")

    out = str(Path(__file__).resolve().parent.parent / "tts_test.wav")
    log(f"synthesizing on {dev}  <-- if it hangs HERE, it's compute ...")
    tts.tts_to_file(
        text="你好呀，我是爱莉希雅。今天也要元气满满哦。",
        file_path=out,
        language="zh-cn",
        speaker="Ana Florence",
    )
    log(f"wrote wav -> {out}")

    log("playing wav  <-- if it hangs HERE, it's audio playback ...")
    try:
        from playsound import playsound
        playsound(out)
        log("playback done")
    except Exception as e:
        log(f"playsound failed ({e}); open {out} manually to hear it")

    log("ALL DONE")


if __name__ == "__main__":
    main()
