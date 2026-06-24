"""GPT-SoVITS backend — call a local GPT-SoVITS inference server (api_v2.py).

GPT-SoVITS gives a purpose-trained, character-accurate voice (much better than
XTTS zero-shot for someone like Elysia), runs locally on your GPU, and is fast
enough for live use. This backend just talks to its HTTP API; the heavy model
lives in the GPT-SoVITS process.

Setup (see GPTSOVITS_SETUP.md):
  1. Install GPT-SoVITS (the CN one-click 整合包 is easiest) and an Elysia model
     (a GPT .ckpt + a SoVITS .pth) plus a short reference clip + its transcript.
  2. Start its API:  python api_v2.py   (serves http://127.0.0.1:9880)
  3. In config.json set:
       "tts_backend": "gptsovits",
       "gptsovits_ref_audio": "C:/.../elysia_ref.wav",
       "gptsovits_prompt_text": "<exact transcript of that clip>",
       "gptsovits_prompt_lang": "zh"
     (optionally gptsovits_gpt_weights / gptsovits_sovits_weights to auto-load).

Dependency-free (urllib). Returns WAV.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import TTSBackend, detect_lang

# our lang code -> GPT-SoVITS text_lang code
_LANG_MAP = {"zh": "zh", "en": "en"}


class GPTSoVITSBackend(TTSBackend):
    def __init__(self, url: str = "http://127.0.0.1:9880",
                 ref_audio: str = "", prompt_text: str = "", prompt_lang: str = "zh",
                 gpt_weights: str = "", sovits_weights: str = "",
                 top_k: int = 15, top_p: float = 1.0, temperature: float = 1.0,
                 speed: float = 1.0, text_split_method: str = "cut5",
                 timeout_s: int = 120):
        self.url = url.rstrip("/")
        self.ref_audio = ref_audio
        self.prompt_text = prompt_text
        self.prompt_lang = prompt_lang
        self.gpt_weights = gpt_weights
        self.sovits_weights = sovits_weights
        self.top_k = top_k
        self.top_p = top_p
        self.temperature = temperature
        self.speed = speed
        self.text_split_method = text_split_method
        self.timeout_s = timeout_s
        self._weights_loaded = False

    # --- helpers ---
    def _get(self, path: str, params: dict, timeout: int):
        q = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{self.url}{path}?{q}", method="GET")
        return urllib.request.urlopen(req, timeout=timeout)

    def _ensure_weights(self):
        """Load the Elysia GPT/SoVITS weights into the server once, if configured."""
        if self._weights_loaded:
            return
        try:
            if self.sovits_weights:
                self._get("/set_sovits_weights", {"weights_path": self.sovits_weights}, 60).read()
            if self.gpt_weights:
                self._get("/set_gpt_weights", {"weights_path": self.gpt_weights}, 60).read()
        except Exception:
            pass  # server may already have them from its own config
        self._weights_loaded = True

    # --- TTSBackend API ---
    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        if not out_path.endswith(".wav"):
            out_path = out_path.rsplit(".", 1)[0] + ".wav"
        tlang = _LANG_MAP.get(lang or detect_lang(text), "auto")
        self._ensure_weights()
        payload = {
            "text": text,
            "text_lang": tlang,
            "ref_audio_path": self.ref_audio,
            "prompt_text": self.prompt_text,
            "prompt_lang": self.prompt_lang,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "speed_factor": self.speed,
            "text_split_method": self.text_split_method,
            "media_type": "wav",
            "streaming_mode": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/tts", data=data, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            body = resp.read()
        # success = audio bytes; failure = a JSON error object
        if body[:1] in (b"{", b"["):
            try:
                err = json.loads(body.decode("utf-8"))
                raise RuntimeError(f"GPT-SoVITS error: {err}")
            except ValueError:
                pass
        with open(out_path, "wb") as f:
            f.write(body)
        return out_path

    def warmup(self) -> str:
        self._ensure_weights()
        return "gpt-sovits"

    def is_available(self) -> tuple[bool, str]:
        if not self.ref_audio:
            return False, "set gptsovits_ref_audio (+ gptsovits_prompt_text) in config.json"
        try:
            # any HTTP response means the server is up (root may 404 — that's fine)
            urllib.request.urlopen(self.url, timeout=3)
            return True, f"GPT-SoVITS server at {self.url}"
        except urllib.error.HTTPError:
            return True, f"GPT-SoVITS server at {self.url}"
        except Exception:
            return False, f"GPT-SoVITS server not reachable at {self.url} (start api_v2.py)"

    @property
    def name(self) -> str:
        return "gptsovits"

    @property
    def output_ext(self) -> str:
        return ".wav"
