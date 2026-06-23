"""Coqui XTTS v2 backend — local, offline, voice-cloning, bilingual (EN/ZH).

Heavier than edge-tts (downloads a model, uses GPU/CPU) but fully local and lets you
clone a target voice from a short reference clip. Install: pip install TTS

Give it a `speaker_wav` (6-20s clip of the target voice) to clone, or it will ask you
to supply one. Outputs WAV (easy to play on Windows).
"""

from __future__ import annotations

import os

from .base import TTSBackend, detect_lang

# XTTS uses 'zh-cn' rather than 'zh'.
_LANG_MAP = {"zh": "zh-cn", "en": "en"}


class XTTSBackend(TTSBackend):
    def __init__(self, speaker_wav: str = "", model: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.speaker_wav = speaker_wav
        self.model_name = model
        self._tts = None  # lazy-loaded model

    def _load(self):
        if self._tts is None:
            from TTS.api import TTS  # lazy
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tts = TTS(self.model_name).to(device)
        return self._tts

    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        if not self.speaker_wav or not os.path.exists(self.speaker_wav):
            raise FileNotFoundError(
                "XTTS needs a reference voice. Set `xtts_speaker_wav` in config.json to a "
                "6-20s WAV clip of the voice you want Elysia to use."
            )
        if not out_path.endswith(".wav"):
            out_path = out_path.rsplit(".", 1)[0] + ".wav"
        xlang = _LANG_MAP.get(lang or detect_lang(text), "en")
        tts = self._load()
        tts.tts_to_file(text=text, file_path=out_path,
                        speaker_wav=self.speaker_wav, language=xlang)
        return out_path

    def is_available(self) -> tuple[bool, str]:
        try:
            import TTS  # noqa: F401
        except ImportError:
            return False, "Coqui TTS not installed. Run: pip install TTS"
        if not self.speaker_wav:
            return False, "XTTS ready, but set `xtts_speaker_wav` to a reference voice clip."
        return True, f"XTTS ready (speaker={self.speaker_wav})"

    @property
    def name(self) -> str:
        return "xtts"

    @property
    def output_ext(self) -> str:
        return ".wav"
