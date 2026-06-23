"""Built-in web avatar — a lightweight lip-sync face for OBS (no Live2D rig needed).

Serves a small HTML face (avatar/web/face.html) on localhost and a /state endpoint
the app updates. The page polls /state and animates: mouth flaps while `speaking`,
cheeks/brows shift with `emotion`. The background is green for easy OBS chroma-key.

Add it in OBS as a Browser Source pointing at http://127.0.0.1:8010 .

Stdlib only. A real Live2D model later just means swapping this for VTubeStudioAvatar.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .base import AvatarController

_HTML_PATH = os.path.join(os.path.dirname(__file__), "web", "face.html")


class WebAvatar(AvatarController):
    def __init__(self, host: str = "127.0.0.1", port: int = 8010, name: str = "Elysia"):
        self.host = host
        self.port = port
        self._state = {"speaking": False, "emotion": "neutral", "name": name}
        self._srv = None
        self._thread = None

    def connect(self) -> tuple[bool, str]:
        state = self._state
        try:
            with open(_HTML_PATH, "r", encoding="utf-8") as f:
                html = f.read().encode("utf-8")
        except OSError as e:
            return False, f"avatar HTML missing: {e}"

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/state"):
                    self._send(200, json.dumps(state).encode("utf-8"), "application/json")
                else:
                    self._send(200, html, "text/html; charset=utf-8")

            def log_message(self, *a):
                pass

        try:
            self._srv = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as e:
            return False, f"avatar port {self.port} busy: {e}"
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        return True, f"web avatar at http://{self.host}:{self.port} (add as OBS Browser Source)"

    def set_emotion(self, emotion: str) -> None:
        self._state["emotion"] = emotion or "neutral"

    def speak_start(self) -> None:
        self._state["speaking"] = True

    def speak_end(self) -> None:
        self._state["speaking"] = False

    def close(self) -> None:
        try:
            if self._srv:
                self._srv.shutdown()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return "web"
