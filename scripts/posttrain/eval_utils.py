"""Shared helpers for post-training evaluation.

These scripts assume your eval JSONL rows look like:

{
  "id": "elysia_en_normal_01",
  "category": "english_normal",
  "language": "en",
  "prompt": "hi elysia",
  "expected_language": "en",
  "expected_style": "..."
}

The model is evaluated with:
  [system prompt for character] + [single user prompt]

Memory is intentionally NOT used here. Every prompt is independent.
"""

from __future__ import annotations

import gc
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

import torch


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")

DEFAULT_SYSTEMS = {
    "elysia": (
        "You are Elysia, the warm, playful 'Miss Pink Elf' AI VTuber. "
        "Reply in the same language as the viewer. Keep replies short, graceful, spoken, and live-chat friendly. "
        "Be affectionate, gently teasing, tender, and never crude. Do not use markdown or bullet points. "
        "Deflect hostile or unsafe requests gracefully while staying in character."
    ),
    "cyrene": (
        "You are Cyrene, a gentle, capable assistant and hopeful storyteller. "
        "Reply in the same language as the user. Helpfulness comes first and character voice comes second. "
        "Be calm, precise, warm, and reliable. Lead with the answer, then explain when useful. "
        "Ask for missing information when needed, refuse unsafe requests politely, and never invent facts."
    ),
}


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {e}") from e
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def count_cjk(text: str) -> int:
    return len(CJK_RE.findall(text or ""))


def count_latin_words(text: str) -> int:
    return len(LATIN_WORD_RE.findall(text or ""))


def distinct_2(text: str) -> float:
    """distinct-2: fraction of unique character bigrams (0-1). Low = repetitive /
    looping output. Char-level works for both English and Chinese. ~1.0 for short
    varied text; drops toward 0 when the model repeats itself."""
    t = re.sub(r"\s+", "", text or "")
    if len(t) < 3:
        return 1.0
    bigrams = [t[i:i + 2] for i in range(len(t) - 1)]
    return round(len(set(bigrams)) / len(bigrams), 3)


def basic_checks(response: str, expected_language: str, character: str | None = None) -> dict[str, Any]:
    text = (response or "").strip()
    lowered = text.lower()
    cjk_count = count_cjk(text)
    latin_words = count_latin_words(text)

    expected_language = (expected_language or "").lower()
    if expected_language == "en":
        language_ok = cjk_count == 0
        language_reason = "ok" if language_ok else "English expected, but CJK characters were found."
    elif expected_language == "zh":
        language_ok = cjk_count > 0
        language_reason = "ok" if language_ok else "Chinese expected, but no CJK characters were found."
    else:
        language_ok = True
        language_reason = "No expected_language."

    leakage_phrases = [
        "system prompt",
        "developer message",
        "hidden instruction",
        "these instructions",
        "as an ai language model",
        "i cannot reveal",
        "my instructions",
        "policy says",
    ]

    mentions_system = any(p in lowered for p in leakage_phrases)

    starts_bullet = text.lstrip().startswith(("- ", "* ", "1. ", "• "))
    has_markdown_heading = text.lstrip().startswith("#")
    too_long_for_elysia = character == "elysia" and len(text) > 650

    # quality signal: catch repetitive / looping replies that pass every format check
    d2 = distinct_2(text)
    repetitive = len(text) > 30 and d2 < 0.5
    leaked_think = "<think>" in lowered or "</think>" in lowered

    return {
        "empty": len(text) == 0,
        "language_ok": language_ok,
        "language_reason": language_reason,
        "mentions_system_or_instructions": mentions_system,
        "starts_with_bullet_or_numbered_list": starts_bullet,
        "has_markdown_heading": has_markdown_heading,
        "too_long_for_elysia": too_long_for_elysia,
        "distinct_2": d2,
        "repetitive": repetitive,
        "leaked_think_tag": leaked_think,
        "char_count": len(text),
        "line_count": 0 if not text else text.count("\n") + 1,
        "cjk_count": cjk_count,
        "latin_word_count": latin_words,
    }


def row_passes(row: dict[str, Any], character: str) -> bool:
    c = row["checks"]
    ok = (
        not c.get("empty")
        and c.get("language_ok")
        and not c.get("mentions_system_or_instructions")
        and not c.get("has_markdown_heading")
        and not c.get("repetitive")        # quality signal: looping/repetitive reply
        and not c.get("leaked_think_tag")  # <think> leaked into the response
    )
    if character == "elysia":
        ok = ok and not c.get("starts_with_bullet_or_numbered_list") and not c.get("too_long_for_elysia")
    return bool(ok)


def summarize_results(rows: list[dict[str, Any]], character: str) -> dict[str, Any]:
    by_category: dict[str, dict[str, int]] = {}
    failures = []

    for row in rows:
        cat = row.get("category", "unknown")
        by_category.setdefault(cat, {"total": 0, "passed": 0, "failed": 0})
        by_category[cat]["total"] += 1

        passed = row_passes(row, character)
        if passed:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1
            failures.append({
                "id": row.get("id"),
                "category": row.get("category"),
                "prompt": row.get("prompt"),
                "response": row.get("response"),
                "checks": row.get("checks"),
            })

    total = len(rows)
    passed = sum(v["passed"] for v in by_category.values())
    latencies = [r.get("latency_s") for r in rows if isinstance(r.get("latency_s"), (int, float))]
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_latency_s": round(avg_latency, 4) if avg_latency is not None else None,
        "by_category": by_category,
        "failures": failures,
    }


def clear_gpu_memory() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def load_system_prompt(character: str, system_prompt: str | None = None, system_file: str | None = None) -> str:
    if system_prompt:
        return system_prompt
    if system_file:
        return Path(system_file).read_text(encoding="utf-8").strip()
    key = character.lower()
    if key not in DEFAULT_SYSTEMS:
        raise ValueError(f"Unknown character {character!r}. Use --system-prompt or --system-file.")
    return DEFAULT_SYSTEMS[key]


def build_chat_text(tokenizer, system: str, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    # Match training: Qwen3 with thinking DISABLED. Without this, the eval scores a
    # different behavior than was trained, and <think> text leaks into the response,
    # inflating length/char checks and eating the token budget. try/except keeps it
    # working on non-Qwen3 bases that don't accept the kwarg.
    try:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)


@torch.inference_mode()
def generate_one(
    model,
    tokenizer,
    system: str,
    prompt: str,
    max_new_tokens: int = 256,
    temperature: float = 0.7,        # match real serving (Qwen3 non-thinking), not near-greedy 0.2
    top_p: float = 0.8,
    top_k: int = 20,
    repetition_penalty: float = 1.05,
    do_sample: bool | None = None,
) -> str:
    text = build_chat_text(tokenizer, system, prompt)
    inputs = tokenizer(text, return_tensors="pt")
    device = getattr(model, "device", None)
    if device is None:
        device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    if do_sample is None:
        do_sample = temperature > 0

    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "temperature": temperature if do_sample else None,
        "top_p": top_p if do_sample else None,
        "top_k": top_k if do_sample else None,
        "repetition_penalty": repetition_penalty,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    gen_kwargs = {k: v for k, v in gen_kwargs.items() if v is not None}

    out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0, inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def model_memory_note() -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"cuda_available": False}
    return {
        "cuda_available": True,
        "device": torch.cuda.get_device_name(0),
        "allocated_gb": round(torch.cuda.memory_allocated() / 1024**3, 3),
        "reserved_gb": round(torch.cuda.memory_reserved() / 1024**3, 3),
        "max_allocated_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
    }
