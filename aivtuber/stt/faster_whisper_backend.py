"""faster-whisper STT backend — local, fast, multilingual (EN/ZH).

Install: pip install faster-whisper
Models: tiny, base, small, medium, large-v3 (bigger = more accurate, slower).
On your RTX 4060, device='cuda' with compute_type='float16' is fast; CPU works too
(use compute_type='int8'). The model auto-detects English vs Chinese.
"""

from __future__ import annotations

from .base import STTBackend


class FasterWhisperBackend(STTBackend):
    def __init__(self, model_size: str = "base", device: str = "auto",
                 compute_type: str = "auto", language: str | None = None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language  # None = auto-detect EN/ZH
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            device = self.device
            compute = self.compute_type
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    device = "cpu"
            if compute == "auto":
                compute = "float16" if device == "cuda" else "int8"
            self._model = WhisperModel(self.model_size, device=device, compute_type=compute)
        return self._model

    def transcribe(self, wav_path: str) -> str:
        model = self._load()
        segments, _info = model.transcribe(wav_path, language=self.language, vad_filter=True)
        return "".join(seg.text for seg in segments).strip()

    def is_available(self) -> tuple[bool, str]:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False, "faster-whisper not installed. Run: pip install faster-whisper"
        return True, f"faster-whisper ready (model={self.model_size})"

    @property
    def name(self) -> str:
        return "faster-whisper"
