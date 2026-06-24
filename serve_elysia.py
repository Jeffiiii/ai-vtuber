"""Serve the fine-tuned (merged) model over a tiny local HTTP API.

A no-GGUF, no-Ollama, no-GitHub way to use your fine-tuned Elysia: loads the merged
HF model in 4-bit (fits your 8GB GPU) and exposes a minimal endpoint the app's
`local_http` provider calls. Run this in WSL (.venv-train); run the app against it.

    python serve_elysia.py --model ~/ai-vtuber/output/elysia-merged
    # then in config.elysia.json set:  "llm_provider": "local_http"

Endpoints:
    GET  /health                -> {"ok": true, "model": "..."}
    POST /generate {messages,temperature,max_tokens} -> {"text": "..."}

Stdlib HTTP only (no fastapi/uvicorn needed). One request at a time (a lock guards
the GPU). Good enough to chat with and drive the voice/autonomous loops.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

_LOCK = threading.Lock()
_TOK = None
_MODEL = None
_NAME = ""


def load_model(model_path: str):
    global _TOK, _MODEL, _NAME
    print(f"Loading {model_path} in 4-bit…")
    _TOK = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if _TOK.pad_token is None:
        _TOK.pad_token = _TOK.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    _MODEL = AutoModelForCausalLM.from_pretrained(
        model_path, quantization_config=bnb, device_map={"": 0}, trust_remote_code=True)
    _MODEL.eval()
    _NAME = os.path.basename(os.path.normpath(model_path))
    print(f"Ready. GPU: {torch.cuda.get_device_name(0)}")


def generate(messages, temperature: float, max_tokens: int) -> str:
    kwargs = dict(tokenize=False, add_generation_prompt=True)
    try:
        prompt = _TOK.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        prompt = _TOK.apply_chat_template(messages, **kwargs)
    inputs = _TOK(prompt, return_tensors="pt").to(_MODEL.device)
    n_in = inputs["input_ids"].shape[1]
    with _LOCK, torch.no_grad():
        out = _MODEL.generate(
            **inputs, max_new_tokens=max_tokens,
            do_sample=temperature > 0, temperature=max(temperature, 1e-5),
            top_p=0.9, repetition_penalty=1.15, pad_token_id=_TOK.eos_token_id)
    return _TOK.decode(out[0][n_in:], skip_special_tokens=True).strip()


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        # Allow the static website (any local origin) to call this from the browser.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        # CORS preflight for the browser fetch from the website.
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "model": _NAME})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/generate":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            text = generate(req.get("messages", []),
                            float(req.get("temperature", 0.85)),
                            int(req.get("max_tokens", 400)))
            self._send(200, {"text": text})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def log_message(self, *a):
        pass  # quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.path.expanduser("~/ai-vtuber/output/elysia-merged"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    load_model(args.model)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
