"""Microphone capture helper for STT.

Records 16 kHz mono audio to a temp WAV the STT backend can transcribe.
Install: pip install sounddevice soundfile

Two modes:
  record_fixed(seconds)        — record a fixed duration (simplest; good to start)
  record_until_silence(...)    — push-to-talk style: stop after a pause (basic VAD)

A full barge-in / interruption loop comes in Stage 3; this is enough to talk to
Elysia now.
"""

from __future__ import annotations

import tempfile

SAMPLE_RATE = 16000


def record_fixed(seconds: float = 5.0) -> str:
    """Record `seconds` of mono 16 kHz audio; return the temp WAV path."""
    import sounddevice as sd
    import soundfile as sf

    print(f"[mic] Recording {seconds:.0f}s… speak now.")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="int16")
    sd.wait()
    path = tempfile.mktemp(suffix=".wav")
    sf.write(path, audio, SAMPLE_RATE)
    return path


def record_until_silence(max_seconds: float = 15.0, silence_secs: float = 1.2,
                         threshold: float = 0.012) -> str:
    """Record until ~`silence_secs` of quiet (basic energy VAD) or `max_seconds`.

    Returns the temp WAV path. Tune `threshold` to your mic if it cuts off early
    or never stops.
    """
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    block = int(0.1 * SAMPLE_RATE)  # 100 ms blocks
    chunks: list = []
    silent_blocks = 0
    needed_silent = int(silence_secs / 0.1)
    max_blocks = int(max_seconds / 0.1)
    started = False

    print("[mic] Listening… (speak, then pause)")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        for _ in range(max_blocks):
            data, _ = stream.read(block)
            chunks.append(data.copy())
            energy = float(np.sqrt(np.mean(data ** 2)))
            if energy >= threshold:
                started = True
                silent_blocks = 0
            elif started:
                silent_blocks += 1
                if silent_blocks >= needed_silent:
                    break

    import numpy as np
    audio = np.concatenate(chunks) if chunks else np.zeros((1, 1), dtype="float32")
    audio_i16 = (np.clip(audio, -1, 1) * 32767).astype("int16")
    path = tempfile.mktemp(suffix=".wav")
    sf.write(path, audio_i16, SAMPLE_RATE)
    return path
