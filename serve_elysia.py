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
import datetime
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)

_LOCK = threading.Lock()
_TOK = None
_MODEL = None
_NAME = ""

# optional reactive substrate for the website chat (memory + mood + rich per-turn log).
# Stays None if the module/OLV isn't reachable, in which case we just serve raw.
try:
    import reactive_brain
except Exception:
    reactive_brain = None

# --- web-chat feedback log (the GitHub-Pages chat path) -----------------------------------
# The website's chat talks to THIS server directly (no OLV substrate), so its turns never reach
# OLV's reactive turn-log. This captures them as a thin transcript: input + reply + latency, one
# JSONL line per turn. Not the rich §1.1 record (no memory/mood here) — but enough to read what
# friends said on the public chat and spot rough lines. Off if --log-dir "".
_LOG_DIR = ""
_LOG_LOCK = threading.Lock()


def _lang_of(text: str):
    if not text or not text.strip():
        return None
    return "zh" if any("一" <= ch <= "鿿" for ch in text) else "en"


def _weblog(endpoint: str, messages: list, reply: str, latency_ms: int) -> None:
    """Append one transcript line for a website-chat turn. Never raises."""
    if not _LOG_DIR:
        return
    try:
        user = ""
        for m in reversed(messages or []):
            if m.get("role") == "user":
                user = m.get("content", "")
                break
        rec = {
            "ts": time.time(),
            "source": "web_chat",
            "endpoint": endpoint,
            "user": user,
            "reply": reply,
            "lang_user": _lang_of(user),
            "lang_reply": _lang_of(reply),
            "latency_ms": latency_ms,
        }
        day = datetime.datetime.now().strftime("%Y-%m-%d")
        with _LOG_LOCK:
            os.makedirs(_LOG_DIR, exist_ok=True)
            with open(os.path.join(_LOG_DIR, f"{day}.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


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


def generate_stream(messages, temperature: float, max_tokens: int):
    """Yield text chunks as they're generated (for OpenAI-style SSE → OLV).
    Uses Qwen3 non-thinking sampling (~temp 0.7 / top_p 0.8 / top_k 20)."""
    kwargs = dict(tokenize=False, add_generation_prompt=True)
    try:
        prompt = _TOK.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        prompt = _TOK.apply_chat_template(messages, **kwargs)
    inputs = _TOK(prompt, return_tensors="pt").to(_MODEL.device)
    streamer = TextIteratorStreamer(_TOK, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(
        **inputs, max_new_tokens=max_tokens, do_sample=temperature > 0,
        temperature=max(temperature, 1e-5), top_p=0.8, top_k=20,
        repetition_penalty=1.1, pad_token_id=_TOK.eos_token_id, streamer=streamer)

    def _run():
        with _LOCK, torch.no_grad():
            _MODEL.generate(**gen_kwargs)

    threading.Thread(target=_run, daemon=True).start()
    for text in streamer:
        if text:
            yield text


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
        elif self.path in ("/v1/models", "/models"):     # OLV / OpenAI clients probe this
            self._send(200, {"object": "list",
                             "data": [{"id": _NAME or "elysia", "object": "model"}]})
        else:
            self._send(404, {"error": "not found"})

    def _openai_chat(self):
        """OpenAI-compatible /v1/chat/completions (stream + non-stream) for OLV."""
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length).decode("utf-8"))
        messages = req.get("messages", [])
        temperature = float(req.get("temperature", 0.7))
        max_tokens = int(req.get("max_tokens") or req.get("max_completion_tokens") or 400)
        stream = bool(req.get("stream", False))
        mid, created = "chatcmpl-elysia", int(time.time())
        _t0 = time.perf_counter()
        if stream:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            _full = ""
            try:
                for chunk in generate_stream(messages, temperature, max_tokens):
                    _full += chunk
                    payload = {"id": mid, "object": "chat.completion.chunk",
                               "created": created, "model": _NAME,
                               "choices": [{"index": 0, "delta": {"content": chunk},
                                            "finish_reason": None}]}
                    self.wfile.write(
                        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                end = {"id": mid, "object": "chat.completion.chunk", "created": created,
                       "model": _NAME,
                       "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                self.wfile.write(f"data: {json.dumps(end)}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            _weblog("/v1/chat/completions", messages, _full,
                    round((time.perf_counter() - _t0) * 1000))
        else:
            text = generate(messages, temperature, max_tokens)
            _weblog("/v1/chat/completions", messages, text,
                    round((time.perf_counter() - _t0) * 1000))
            self._send(200, {"id": mid, "object": "chat.completion", "created": created,
                             "model": _NAME,
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant", "content": text}}],
                             "usage": {}})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            try:
                self._openai_chat()
            except Exception as e:
                self._send(500, {"error": str(e)})
            return
        if self.path != "/generate":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            _msgs = req.get("messages", [])
            _sid = req.get("session_id")
            _temp = float(req.get("temperature", 0.85))
            _max = int(req.get("max_tokens", 400))
            if reactive_brain and reactive_brain.enabled() and _sid:
                # full substrate: memory recall + caused mood + consolidation + rich turn-log
                text = reactive_brain.chat(generate, _sid, _msgs, _temp, _max)
            else:
                _t0 = time.perf_counter()
                text = generate(_msgs, _temp, _max)
                _weblog("/generate", _msgs, text, round((time.perf_counter() - _t0) * 1000))
            self._send(200, {"text": text})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def log_message(self, *a):
        pass  # quiet


def main():
    global _LOG_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.path.expanduser("~/ai-vtuber/output/elysia-merged"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--log-dir", default="logs/web_chat",
                    help="where to write raw website-chat transcripts (set '' to disable)")
    ap.add_argument("--reactive", action="store_true",
                    help="run the reactive substrate (memory/mood/rich log) for web-chat "
                         "requests that include a session_id")
    ap.add_argument("--olv-src", default="/mnt/c/Users/Leo12/Documents/Open-LLM-VTuber/src",
                    help="path to OLV's src/ (the reactive memory + mood modules live there)")
    ap.add_argument("--reactive-memory-dir", default="cache/web_memory")
    ap.add_argument("--reactive-log-dir", default="logs/reactive_turns_web")
    args = ap.parse_args()
    _LOG_DIR = args.log_dir or ""
    if _LOG_DIR:
        print(f"Web-chat transcripts -> {os.path.abspath(_LOG_DIR)}/<date>.jsonl")
    if args.reactive:
        if reactive_brain:
            reactive_brain.init(args.olv_src, args.reactive_memory_dir, args.reactive_log_dir)
        else:
            print("--reactive requested but reactive_brain.py not importable; serving raw.")
    load_model(args.model)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
