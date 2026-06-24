"""GSVI backend — call the GPT-SoVITS-Inference (GSVI) server.

The "1007" GPT-SoVITS package ships GSVI, a richer inference server that loads a
character model from `models/<version>/<name>/` (with bundled emotion reference
clips) and exposes `/infer_single`. This backend calls it, so the app uses the
real trained Elysia voice.

Start GSVI on a free port (8000 is taken by the LLM server):
    runtime\\python.exe gsvi.py -p 8002

Then in config.json:
    "tts_backend": "gsvi",
    "gsvi_url": "http://127.0.0.1:8002",
    "gsvi_model_name": "爱莉希雅",
    "gsvi_version": "v4",
    "gsvi_emotion": "默认",
    "gsvi_prompt_lang": "中文"

Dependency-free (urllib). Returns WAV.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import TTSBackend, detect_lang

# our lang code -> GSVI's Chinese display label (it maps these internally)
_LANG_LABEL = {"zh": "中文", "en": "英语"}
_MIXED = "多语种混合"   # auto-detect; good for occasional EN inside ZH


class GSVIBackend(TTSBackend):
    def __init__(self, url: str = "http://127.0.0.1:8002",
                 model_name: str = "", version: str = "v4",
                 emotion: str = "默认", prompt_lang: str = "中文",
                 top_k: int = 10, top_p: float = 1.0, temperature: float = 1.0,
                 speed: float = 1.0, repetition_penalty: float = 1.35,
                 text_split_method: str = "按标点符号切", timeout_s: int = 120):
        self.url = url.rstrip("/")
        self.model_name = model_name
        self.version = version
        self.emotion = emotion
        self.prompt_lang = prompt_lang
        self.top_k = top_k
        self.top_p = top_p
        self.temperature = temperature
        self.speed = speed
        self.repetition_penalty = repetition_penalty
        self.text_split_method = text_split_method
        self.timeout_s = timeout_s
        # Never route localhost calls through a system proxy (avoids odd failures
        # when http_proxy/https_proxy is set in the environment).
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _open(self, req, timeout):
        return self._opener.open(req, timeout=timeout)

    def _text_lang(self, code: str) -> str:
        return _LANG_LABEL.get(code, _MIXED)

    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        if not out_path.endswith(".wav"):
            out_path = out_path.rsplit(".", 1)[0] + ".wav"
        payload = {
            "version": self.version,
            "model_name": self.model_name,
            "prompt_text_lang": self.prompt_lang,
            "emotion": self.emotion,
            "text": text,
            "text_lang": self._text_lang(lang or detect_lang(text)),
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "speed_facter": self.speed,          # note: GSVI spells it "facter"
            "repetition_penalty": self.repetition_penalty,
            "text_split_method": self.text_split_method,
            "media_type": "wav",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/infer_single", data=data, method="POST",
            headers={"Content-Type": "application/json"})
        with self._open(req, self.timeout_s) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        audio_url = res.get("audio_url", "")
        if not audio_url:
            raise RuntimeError(f"GSVI infer failed: {res.get('msg', 'unknown error')}")
        # audio_url = http://<host>:<port>/<path>; refetch by path from our base url
        path = urllib.parse.urlparse(audio_url).path
        with self._open(urllib.request.Request(f"{self.url}{path}"), self.timeout_s) as r:
            body = r.read()
        with open(out_path, "wb") as f:
            f.write(body)
        return out_path

    def warmup(self) -> str:
        try:
            self.is_available()
        except Exception:
            pass
        return f"gsvi ({self.model_name})"

    def is_available(self) -> tuple[bool, str]:
        if not self.model_name:
            return False, "set gsvi_model_name in config.json"
        # /version is the lightest endpoint and proves the server is up.
        reachable = False
        for path in ("/version", "/api", "/"):
            try:
                with self._open(urllib.request.Request(f"{self.url}{path}"), 4) as r:
                    if 200 <= getattr(r, "status", r.getcode()) < 500:
                        reachable = True
                        break
            except urllib.error.HTTPError:
                reachable = True  # server answered (even if 4xx) => it's up
                break
            except Exception:
                continue
        if not reachable:
            port = self.url.rsplit(":", 1)[-1]
            return False, f"GSVI not reachable at {self.url} (start gsvi.py -p {port})"
        # optional model-name sanity check (never blocks)
        try:
            with self._open(urllib.request.Request(f"{self.url}/models/{self.version}"), 4) as r:
                names = [m.get("name", m) if isinstance(m, dict) else m
                         for m in (json.loads(r.read().decode("utf-8")).get("models") or [])]
            if names and self.model_name not in names:
                return True, f"GSVI up; '{self.model_name}' not in {names} — check gsvi_model_name/version"
        except Exception:
            pass
        return True, f"GSVI {self.version} '{self.model_name}' at {self.url}"

    @property
    def name(self) -> str:
        return "gsvi"

    @property
    def output_ext(self) -> str:
        return ".wav"
