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
from pathlib import Path

from .base import TTSBackend, detect_lang

_LANG_MAP = {"zh": "zh-cn", "en": "en"}

_UNPICKLE_PATCHED = False


def _allow_xtts_unpickle(torch):
    """Let the official XTTS checkpoint load under PyTorch 2.6+.

    PyTorch 2.6 changed `torch.load` to default `weights_only=True`, which refuses
    to unpickle the XTTS config objects (XttsConfig, XttsAudioConfig, ...) baked into
    the checkpoint and fails with a `WeightsUnpickler error: Unsupported global`.
    Coqui's model is from a trusted source, so we (1) allow-list those config classes
    and (2) force `weights_only=False` as a fallback for any TTS version differences.
    """
    global _UNPICKLE_PATCHED
    if _UNPICKLE_PATCHED:
        return
    # (1) Allow-list the known XTTS config classes (clean, PyTorch-recommended path).
    safe = []
    try:
        from TTS.tts.configs.xtts_config import XttsConfig
        safe.append(XttsConfig)
    except Exception:
        pass
    try:
        from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
        safe.extend([XttsAudioConfig, XttsArgs])
    except Exception:
        pass
    try:
        from TTS.config.shared_configs import BaseDatasetConfig
        safe.append(BaseDatasetConfig)
    except Exception:
        pass
    try:
        if safe and hasattr(torch.serialization, "add_safe_globals"):
            torch.serialization.add_safe_globals(safe)
    except Exception:
        pass
    # (2) Belt-and-suspenders: default weights_only=False for the trusted checkpoint.
    try:
        _orig_load = torch.load

        def _load_full(*args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _orig_load(*args, **kwargs)

        torch.load = _load_full
    except Exception:
        pass
    _UNPICKLE_PATCHED = True


class XTTSBackend(TTSBackend):
    def __init__(self, speaker_wav: str = "", speaker: str = "Ana Florence",
                 model: str = "tts_models/multilingual/multi-dataset/xtts_v2",
                 device: str = "auto", gen_params: dict | None = None):
        self.speaker_wav = speaker_wav          # clone clip: a file OR a folder of clips
        self.speaker = speaker                  # built-in studio speaker (fallback)
        self.model_name = model
        self.device_pref = (device or "auto").lower()   # "auto" | "cuda" | "cpu"
        self.device = None                      # resolved on load
        # XTTS generation knobs — tame "weird"/unstable tone. Only non-None passed.
        self.gen_params = {k: v for k, v in (gen_params or {}).items() if v is not None}
        self._tts = None

    def _ref_clips(self):
        """Resolve speaker_wav into a list of existing clip paths (or None).

        Accepts a single .wav, or a directory of .wav clips (XTTS blends several
        clean clips into a much more stable, accurate voice than one clip).
        """
        p = (self.speaker_wav or "").strip()
        if not p:
            return None
        path = Path(p)
        if path.is_dir():
            clips = sorted(str(x) for x in path.glob("*.wav"))
            return clips or None
        if path.exists():
            return [str(path)]
        return None

    def _resolve_device(self, torch) -> str:
        if self.device_pref == "cpu":
            return "cpu"
        if self.device_pref == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return "cuda" if torch.cuda.is_available() else "cpu"   # auto

    def _load(self):
        if self._tts is None:
            os.environ.setdefault("COQUI_TOS_AGREED", "1")
            # The model is already on disk; stop first-run network checks (HF / version
            # pings) from hanging the load on a restricted network. This venv reaches the
            # LLM over HTTP, so it never needs to fetch anything online here.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            # The model server (WSL) already holds most of the 8GB GPU; keep XTTS's
            # allocator from fragmenting/over-reserving so both fit.
            os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
            import torch
            _allow_xtts_unpickle(torch)            # PyTorch 2.6+ weights_only fix
            from TTS.api import TTS  # lazy
            self.device = self._resolve_device(torch)
            self._tts = TTS(self.model_name).to(self.device)
        return self._tts

    def warmup(self) -> str:
        """Load the model now (so the slow first load happens at startup, not mid-stream)."""
        self._load()
        return self.device or "?"

    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        if not out_path.endswith(".wav"):
            out_path = out_path.rsplit(".", 1)[0] + ".wav"
        xlang = _LANG_MAP.get(lang or detect_lang(text), "en")
        tts = self._load()
        kwargs = dict(text=text, file_path=out_path, language=xlang)
        clips = self._ref_clips()
        if clips:
            kwargs["speaker_wav"] = clips if len(clips) > 1 else clips[0]  # clone (1+ clips)
        else:
            kwargs["speaker"] = self.speaker              # built-in voice
        # Pass the tuning knobs; older Coqui builds may not accept them, so fall back.
        try:
            tts.tts_to_file(**kwargs, **self.gen_params)
        except TypeError:
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
