"""reactive_brain.py — give the website chat the reactive substrate.

The jeffi GitHub-Pages chat talks to serve_elysia over plain HTTP, so it normally bypasses
OLV's reactive agent (no memory, no mood, no per-turn log). This wraps a raw text generator with
that substrate, reusing OLV's OWN reactive modules (single source of truth) so the website chat
gets memory recall, caused mood, consolidation, and the rich per-turn log the maintenance loop
needs — exactly like the OLV path.

How it's wired: serve_elysia calls `init(...)` once, then for a turn calls
`chat(generate_fn, session_id, messages, temperature, max_tokens)` where
`generate_fn(messages, temperature, max_tokens) -> str` is serve_elysia's own generate(). Per
browser session we keep a MemoryStore + MoodModel, assemble real state into the prompt, generate,
then (OFF the response path, in a thread) apply caused mood, consolidate durable memories, and
append one JSONL turn record to logs/reactive_turns_web/.

It loads OLV's `memory_store`/`mood_model` **by file path** (they're pure stdlib) — bypassing the
package __init__, so there's no loguru/torch dependency and nothing else to install. If the OLV
modules can't be found, `init()` returns False and the caller just serves raw (graceful).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
import threading
import time

_ENABLED = False
_MemoryStore = None
_MoodModel = None
_MEMDIR = "cache/web_memory"
_LOGDIR = "logs/reactive_turns_web"
_SESS: dict = {}
_LOCK = threading.Lock()

_CONSOLIDATE_SYSTEM = "You quietly maintain a companion's private memory. Output only JSON."
_CONSOLIDATE_PROMPT = (
    "From the recent conversation, extract only DURABLE, useful memories about the person or the "
    "relationship (stable facts, preferences, things that happened that matter later) — ignore "
    "small talk. Most turns yield none. Reply ONLY as compact JSON: "
    '{"memories": [{"text": str, "importance": 1-10}], '
    '"profile": {"name": str|null, "summary": str|null, "facts": [str]}}. No other text.'
)


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # register before exec so @dataclass introspection works
    spec.loader.exec_module(mod)
    return mod


def init(olv_src: str, memory_dir: str = "", log_dir: str = "") -> bool:
    """Load OLV's reactive modules by path. Returns True if the substrate is available."""
    global _ENABLED, _MemoryStore, _MoodModel, _MEMDIR, _LOGDIR
    try:
        base = os.path.join(olv_src, "open_llm_vtuber", "agent", "agents", "reactive")
        ms = _load_module("rb_memory_store", os.path.join(base, "memory_store.py"))
        mm = _load_module("rb_mood_model", os.path.join(base, "mood_model.py"))
        _MemoryStore, _MoodModel = ms.MemoryStore, mm.MoodModel
        if memory_dir:
            _MEMDIR = memory_dir
        if log_dir:
            _LOGDIR = log_dir
        os.makedirs(_LOGDIR, exist_ok=True)
        os.makedirs(_MEMDIR, exist_ok=True)
        _ENABLED = True
        print(f"[reactive_brain] ON — memory={_MEMDIR}, log={_LOGDIR}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[reactive_brain] OFF ({e}); serving raw. Check --olv-src points at OLV/src.")
        return False


def enabled() -> bool:
    return _ENABLED


def _session(sid: str):
    with _LOCK:
        s = _SESS.get(sid)
        if s is None:
            mem = _MemoryStore({"memory_dir": _MEMDIR, "retrieve_k": 4})
            mem.load(sid)
            s = {"mem": mem, "mood": _MoodModel({})}
            _SESS[sid] = s
        return s


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if m.get("role") == "user":
            return m.get("content", "") or ""
    return ""


def _lang(t):
    if not t or not t.strip():
        return None
    return "zh" if any("一" <= c <= "鿿" for c in t) else "en"


def _state(mem, mood, query, op):
    lines = []
    p = mem.profile_note(op)
    if p:
        lines.append(p)
    n = mood.note()
    if n:
        lines.append(n)
    r = mem.recall_note(query) if query else ""
    if r:
        lines.append(r)
    if not lines:
        return None
    return ("[your real current state — let it shape your reaction; do not list it]\n"
            + "\n".join(lines))


def _inject(messages, state):
    """Insert the real-state system message right after the persona system message."""
    if not state:
        return messages
    out, done = [], False
    for m in messages:
        out.append(m)
        if not done and m.get("role") == "system":
            out.append({"role": "system", "content": state})
            done = True
    return out if done else [{"role": "system", "content": state}] + list(messages)


def _first_json(text):
    if not text:
        return None
    i = text.find("{")
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except Exception:
                    return None
    return None


def chat(generate_fn, session_id, messages, temperature, max_tokens) -> str:
    """Run one website-chat turn through the substrate. Returns the reply text."""
    sid = (session_id or "web_guest").strip() or "web_guest"
    op = "friend"
    s = _session(sid)
    mem, mood = s["mem"], s["mood"]
    mood.tick()
    mood_before = mood.snapshot()
    query = _last_user(messages)
    state = _state(mem, mood, query, op)
    retrieved = list(getattr(mem, "last_retrieval", []))
    t0 = time.perf_counter()
    text = generate_fn(_inject(messages, state), temperature, max_tokens)
    full_ms = round((time.perf_counter() - t0) * 1000)
    # off the response path: caused mood + consolidation + the per-turn log
    threading.Thread(
        target=_after,
        args=(generate_fn, sid, mem, mood, messages, query, text, retrieved, mood_before, full_ms, op),
        daemon=True,
    ).start()
    return text


def _after(generate_fn, sid, mem, mood, messages, query, reply, retrieved, mood_before, full_ms, op):
    events, written = [], []
    try:
        low = (query or "").lower()
        if any(w in low for w in ("thank", "谢谢", "感谢")):
            mood.apply_event("thanked"); events.append("thanked")
        if any(w in low for w in ("love you", "喜欢你", "想你", "厉害", "棒", "great",
                                  "amazing", "proud", "pretty", "cute", "beautiful", "好可爱", "漂亮")):
            mood.apply_event("praised"); events.append("praised")
        if any(w in low for w in ("stupid", "shut up", "笨", "闭嘴", "boring", "无聊")):
            mood.apply_event("insulted", 0.6); events.append("insulted")
        mem.note_interaction(op)
        written = _consolidate(generate_fn, mem, messages, op)
    except Exception:
        pass
    rec = {
        "ts": time.time(), "source": "web_chat", "session": sid,
        "input": {"source": "user", "from_name": op, "text": query, "lang": _lang(query)},
        "retrieved": retrieved,
        "reply": {"text": reply, "lang": _lang(reply)},
        "mood": {"before": mood_before, "after": mood.snapshot(),
                 "events_applied": events, "attachment": round(mem.attachment(op), 3)},
        "memory_written": written,
        "latency": {"full_ms": full_ms},
        "flagged": False,
    }
    try:
        day = datetime.datetime.now().strftime("%Y-%m-%d")
        with _LOCK:
            with open(os.path.join(_LOGDIR, f"{day}.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _consolidate(generate_fn, mem, messages, op):
    window = [m for m in (messages or []) if m.get("role") in ("user", "assistant")][-6:]
    if len(window) < 2:
        return []
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in window)
    out = generate_fn(
        [{"role": "system", "content": _CONSOLIDATE_SYSTEM},
         {"role": "user", "content": _CONSOLIDATE_PROMPT + f"\n\nConversation:\n{convo}\n\nJSON:"}],
        0.3, 220,
    )
    data = _first_json(out)
    written = []
    if not data:
        return written
    for m in (data.get("memories") or [])[:3]:
        if isinstance(m, dict) and m.get("text"):
            it = mem.add(m["text"], kind="episodic", importance=float(m.get("importance", 5)),
                         pool="operator", source=op)
            written.append({"id": it.id, "text": it.text[:80]})
    prof = data.get("profile") or {}
    if any(prof.get(k) for k in ("name", "summary", "facts")):
        mem.set_profile(op, name=prof.get("name"), summary=prof.get("summary"), facts=prof.get("facts"))
    return written
