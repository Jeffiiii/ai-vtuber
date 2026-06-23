"""Local HTTP provider — talks to serve_elysia.py (transformers backend).

Lets the app use the fine-tuned merged model without GGUF/Ollama: the model runs
in serve_elysia.py and this provider POSTs to it. Non-streaming (returns the full
reply); the base class turns generate() into a one-shot stream, which the Brain
handles fine.
"""

from __future__ import annotations

import json
import urllib.request

from .base import LLMProvider

_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class LocalHTTPProvider(LLMProvider):
    def __init__(self, url: str = "http://127.0.0.1:8000", timeout: int = 300,
                 model_label: str = "elysia-ft (local server)"):
        self._url = (url or "http://127.0.0.1:8000").rstrip("/")
        self._timeout = timeout
        self._label = model_label

    def generate(self, messages, temperature: float = 0.85, max_tokens: int = 400) -> str:
        body = json.dumps({"messages": messages, "temperature": temperature,
                           "max_tokens": max_tokens}).encode("utf-8")
        req = urllib.request.Request(self._url + "/generate", data=body,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with _NO_PROXY.open(req, timeout=self._timeout) as r:
            return json.loads(r.read().decode("utf-8")).get("text", "").strip()

    def health_check(self) -> tuple[bool, str]:
        try:
            with _NO_PROXY.open(self._url + "/health", timeout=5) as r:
                info = json.loads(r.read().decode("utf-8"))
            return True, f"local server OK ({info.get('model', '?')})"
        except Exception:
            return False, (f"Local server not reachable at {self._url}. "
                           f"Start it in WSL: python serve_elysia.py")

    def ensure_ready(self) -> tuple[bool, str]:
        return self.health_check()

    @property
    def provider_name(self) -> str:
        return "LocalHTTP"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return self._label
