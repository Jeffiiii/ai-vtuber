"""Serve Elysia's XTTS voice over a tiny local HTTP API (for the website).

Gives the personal website the SAME voice as the desktop app instead of the
browser's generic Web-Speech voice. Run it in the Windows app venv (the one with
TTS + the CUDA torch). The website calls POST /tts and plays the returned audio;
it falls back to browser speech automatically when this server is off.

    python serve_tts.py                 # uses config.json
    # GET  /health             -> {"ok": true, "voice": "xtts"}
    # POST /tts {text, lang?}   -> audio/wav  (lang: "zh" | "en" | omitted=auto)

To make her sound like Elysia, set "xtts_speaker_wav" in config.json to a clean
6-20s reference clip (see VOICE_CLONING.md); XTTS clones that timbre.

Stdlib HTTP only. One synthesis at a time (a lock guards the GPU). Note: if you
also run the desktop orchestrator with XTTS at the same time, the model loads
twice (≈2x VRAM) — run whichever one you need.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aivtuber.config import load_config          # noqa: E402
from aivtuber.tts import create_tts              # noqa: E402

_LOCK = threading.Lock()
_TTS = None


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "voice": _TTS.name if _TTS else ""})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/tts":
            self._json(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            text = (req.get("text") or "").strip()
            lang = req.get("lang") or None          # "zh" | "en" | None=auto
            if not text:
                self._json(400, {"error": "no text"})
                return
            out = tempfile.mktemp(suffix=_TTS.output_ext)
            with _LOCK:
                _TTS.synthesize(text, out, lang)
            with open(out, "rb") as f:
                data = f.read()
            try:
                os.remove(out)
            except OSError:
                pass
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def log_message(self, *a):
        pass  # quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8020)
    args = ap.parse_args()

    global _TTS
    root = Path(__file__).resolve().parent
    cfg = load_config(root / "config.json")
    _TTS = create_tts(cfg)
    ok, msg = _TTS.is_available()
    print(f"Voice: {_TTS.name} — {msg}")
    if not ok:
        print("  ✗ Voice backend not ready (install requirements-voice.txt)."); return 1
    if hasattr(_TTS, "warmup"):
        print("Warming up (loading model)…", flush=True)
        try:
            print(f"Ready on {_TTS.warmup()}.")
        except Exception as e:
            print(f"Warmup failed ({e}); will load on first request.")

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"TTS serving on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
