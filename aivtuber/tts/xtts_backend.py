"""Coqui XTTS v2 backend — local, offline, bilingual (EN/ZH). Default voice.

Install: pip install TTS

Two ways to give Elysia a voice:
  1) Built-in studio speaker (no clip needed) — set `xtts_speaker` to a built-in
     voice name (default below). Works out of the box.
  2) Voice cloning — set `xtts_speaker_wav` to a 6-20s WAV of a target voice; it
     overrides the built-in speaker.

Outputs WAV (easy to play on Windows). First run downloads the model (~1.8 GB) and
needs you to accept Coqui's license once (set COQUI_TOS_AGREED=1 to skip the prompt).
"""

from __future__ import annotations

import os

from .base import TTSBackend, detect_lang

_LANG_MAP = {"zh": "zh-cn", "en": "en"}


class XTTSBackend(TTSBackend):
    def __init__(self, speaker_wav: str = "", speaker: str = "Ana Florence",
                 model: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.speaker_wav = speaker_wav          # voice-clone clip (optional)
        self.speaker = speaker                  # built-in studio speaker (fallback)
        self.model_name = model
        self._tts = None

    def _load(self):
        if self._tts is None:
            os.environ.setdefault("COQUI_TOS_AGREED", "1")
            from TTS.api import TTS  # lazy
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tts = TTS(self.model_name).to(device)
        return self._tts

    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        if not out_path.endswith(".wav"):
            out_path = out_path.rsplit(".", 1)[0] + ".wav"
        xlang = _LANG_MAP.get(lang or detect_lang(text), "en")
        tts = self._load()
        kwargs = dict(text=text, file_path=out_path, language=xlang)
        if self.speaker_wav and os.path.exists(self.speaker_wav):
            kwargs["speaker_wav"] = self.speaker_wav      # clone
        else:
            kwargs["speaker"] = self.speaker              # built-in voice
        tts.tts_to_file(**kwargs)
        return out_path

    def is_available(self) -> tuple[bool, str]:
        try:
            import TTS  # noqa: F401
        except ImportError:
            return False, "Coqui TTS not installed. Run: pip install TTS"
        if self.speaker_wav:
            return True, f"XTTS ready (cloning {self.speaker_wav})"
        return True, f"XTTS ready (built-in voice '{self.speaker}')"

    @property
    def name(self) -> str:
        return "xtts"

    @property
    def output_ext(self) -> str:
        return ".wav"
