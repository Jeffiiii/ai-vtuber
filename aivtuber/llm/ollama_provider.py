"""Local Ollama provider with lifecycle management.

Distilled from the Conference project's `ollama_provider.py` + `ollama_runtime.py`,
but simplified for an English-speaking persona and made dependency-free (stdlib only).

Robustness carried over from Conference (these are the things that actually bite you
when you ship a local-LLM app):
  * auto-start the Ollama server if it isn't running (`ollama serve`)
  * auto-pull the model on first use if it's missing
  * warm-up via /api/generate (which BLOCKS during cold load) so the first real
    chat request doesn't 503
  * per-request keep_alive (Windows ignores the OLLAMA_KEEP_ALIVE env var)
  * short 503 retry/backoff as a safety net
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Iterator

from .base import LLMProvider

log = logging.getLogger("aivtuber")

# Bypass any system/VPN proxy for the LOCAL server.
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 model: str = "llama3.1:8b", timeout: int = 300,
                 num_ctx: int = 4096, keep_alive: str = "30m",
                 auto_start: bool = True, auto_pull: bool = True):
        base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self._base_url = base_url.replace("://localhost:", "://127.0.0.1:")
        self._model = model
        self._timeout = timeout
        self._num_ctx = num_ctx
        self._keep_alive = keep_alive
        self._auto_start = auto_start
        self._auto_pull = auto_pull
        self._ready = False

    # ------------------------------------------------------------------ HTTP
    def _get(self, path: str, timeout: int = 5):
        req = urllib.request.Request(f"{self._base_url}{path}")
        return _NO_PROXY.open(req, timeout=timeout)

    def _post(self, path: str, body: bytes, timeout: int):
        req = urllib.request.Request(f"{self._base_url}{path}", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        return _NO_PROXY.open(req, timeout=timeout)

    def _server_up(self) -> bool:
        try:
            with self._get("/api/tags", timeout=3):
                return True
        except Exception:
            return False

    def _model_pulled(self) -> bool:
        try:
            with self._get("/api/tags", timeout=5) as r:
                tags = json.loads(r.read().decode("utf-8"))
            names = {m.get("name", "") for m in tags.get("models", [])}
            base = self._model.split(":")[0]
            return any(n == self._model or n.split(":")[0] == base for n in names)
        except Exception:
            return False

    # --------------------------------------------------------------- lifecycle
    def _start_server(self) -> bool:
        if not shutil.which("ollama"):
            return False
        log.info("Starting Ollama server (ollama serve)…")
        try:
            subprocess.Popen(["ollama", "serve"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.warning("Could not start Ollama: %s", e)
            return False
        for _ in range(30):  # wait up to ~15s
            if self._server_up():
                return True
            time.sleep(0.5)
        return False

    def _pull(self) -> bool:
        if not shutil.which("ollama"):
            return False
        print(f"  Pulling model '{self._model}' (first run only, this can take a while)…")
        try:
            subprocess.run(["ollama", "pull", self._model], check=True)
            return True
        except Exception as e:
            log.warning("Pull failed: %s", e)
            return False

    def _warm_up(self):
        """Force a cold load via /api/generate, which blocks until the runner is
        resident — so the first real chat request won't 503."""
        body = json.dumps({
            "model": self._model, "prompt": "hi", "stream": False,
            "keep_alive": self._keep_alive,
            "options": {"num_ctx": self._num_ctx, "num_predict": 1},
        }).encode("utf-8")
        try:
            with self._post("/api/generate", body, self._timeout):
                pass
        except Exception as e:
            log.info("Warm-up note: %s", e)

    def ensure_ready(self) -> tuple[bool, str]:
        """Guarantee: server up -> model pulled -> runner warm. Idempotent."""
        if self._ready:
            return True, "ready"
        if not self._server_up():
            if not (self._auto_start and self._start_server()):
                return False, ("Ollama server is not running. Start it with "
                               "`ollama serve`, or install Ollama from ollama.com.")
        if not self._model_pulled():
            if not (self._auto_pull and self._pull()):
                return False, f"Model '{self._model}' not found. Run: ollama pull {self._model}"
        self._warm_up()
        self._ready = True
        return True, f"Ollama ready ({self._model})"

    # -------------------------------------------------------------- generation
    def _body(self, messages, temperature, max_tokens, stream):
        return json.dumps({
            "model": self._model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self._num_ctx,
                "repeat_penalty": 1.15,
            },
        }).encode("utf-8")

    def stream_generate(self, messages, temperature: float = 0.8,
                        max_tokens: int = 512) -> Iterator[str]:
        ok, msg = self.ensure_ready()
        if not ok:
            raise ConnectionError(msg)
        body = self._body(messages, temperature, max_tokens, stream=True)

        backoffs = [2, 4]
        resp = None
        for attempt in range(1 + len(backoffs)):
            try:
                resp = self._post("/api/chat", body, self._timeout)
                break
            except urllib.error.HTTPError as e:
                if e.code == 503 and attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    self._warm_up()
                    continue
                raise ConnectionError(f"Ollama HTTP {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                raise ConnectionError(f"Ollama not reachable at {self._base_url}: {e}")
        if resp is None:
            raise ConnectionError("Ollama did not respond after retries.")

        try:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = (obj.get("message") or {}).get("content", "")
                if piece:
                    yield piece
                if obj.get("done"):
                    break
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def generate(self, messages, temperature: float = 0.8, max_tokens: int = 512) -> str:
        return "".join(self.stream_generate(messages, temperature, max_tokens)).strip()

    # ------------------------------------------------------------------ status
    def health_check(self) -> tuple[bool, str]:
        if not shutil.which("ollama") and not self._server_up():
            return False, "Ollama not installed/running. Get it at https://ollama.com"
        if not self._server_up():
            return True, "Ollama installed but not running — will auto-start on first use."
        if not self._model_pulled():
            return True, f"Server up; model '{self._model}' will be pulled on first use."
        return True, f"Ollama OK ({self._model})"

    @property
    def provider_name(self) -> str: return "Ollama"

    @property
    def is_local(self) -> bool: return True

    @property
    def model_name(self) -> str: return self._model
