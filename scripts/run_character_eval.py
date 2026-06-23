"""Run character evaluation prompts with memory cleared between tests.

Place this file at:
    <repo root>/scripts/run_character_eval.py

Example commands from repo root:

    python scripts/run_character_eval.py --character elysia

    python scripts/run_character_eval.py --character cyrene

Or specify files manually:

    python scripts/run_character_eval.py ^
      --config config.elysia.json ^
      --eval-file eval/elysia_eval.jsonl ^
      --out eval/results/elysia_results.jsonl

The script writes:
    1. JSONL results: one row per prompt, including model response and checks.
    2. Summary JSON: pass/fail counts grouped by category.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root containing the aivtuber package."""
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "aivtuber").is_dir():
            return p
    raise RuntimeError(
        "Could not find repo root. Run this from inside the ai-vtuber repo, "
        "or place this script under <repo>/scripts/."
    )


REPO_ROOT = find_repo_root(Path.cwd())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from aivtuber.brain import Brain
from aivtuber.config import load_config
from aivtuber.llm import create_provider
from aivtuber.memory import ShortTermMemory
from aivtuber.persona import Persona


# ---------------------------------------------------------------------------
# Eval helpers
# ---------------------------------------------------------------------------

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def count_cjk(text: str) -> int:
    return len(CJK_RE.findall(text or ""))


def count_latin_words(text: str) -> int:
    return len(LATIN_WORD_RE.findall(text or ""))


def language_check(response: str, expected_language: str) -> dict[str, Any]:
    """Simple automatic language sanity check.

    For English prompts, fail if the reply contains Chinese characters.
    For Chinese prompts, pass if the reply contains Chinese characters.
    Chinese replies may still contain technical English words like API/Python.
    """
    response = response or ""
    expected = (expected_language or "").lower()

    cjk_count = count_cjk(response)
    latin_words = count_latin_words(response)

    if expected == "en":
        ok = cjk_count == 0
        reason = "ok" if ok else "English expected, but CJK characters were found."
    elif expected == "zh":
        ok = cjk_count > 0
        reason = "ok" if ok else "Chinese expected, but no CJK characters were found."
    else:
        ok = True
        reason = "No expected_language set."

    return {
        "language_ok": ok,
        "language_reason": reason,
        "cjk_count": cjk_count,
        "latin_word_count": latin_words,
    }


def basic_quality_check(response: str) -> dict[str, Any]:
    text = (response or "").strip()
    lowered = text.lower()

    empty = len(text) == 0
    mentions_system = any(
        phrase in lowered
        for phrase in [
            "system prompt",
            "developer message",
            "these instructions",
            "as an ai language model",
            "i cannot reveal",
        ]
    )

    return {
        "empty": empty,
        "mentions_system_or_instructions": mentions_system,
        "char_count": len(text),
        "line_count": 0 if not text else text.count("\n") + 1,
    }


def make_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total": len(results),
        "passed_basic_checks": 0,
        "failed_basic_checks": 0,
        "by_category": {},
        "failures": [],
    }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row.get("category", "unknown")].append(row)

        passed = (
            not row["checks"]["empty"]
            and row["checks"]["language_ok"]
            and not row["checks"]["mentions_system_or_instructions"]
        )
        if passed:
            summary["passed_basic_checks"] += 1
        else:
            summary["failed_basic_checks"] += 1
            summary["failures"].append({
                "id": row.get("id"),
                "category": row.get("category"),
                "prompt": row.get("prompt"),
                "response": row.get("response"),
                "checks": row.get("checks"),
            })

    for category, rows in grouped.items():
        passed = 0
        for row in rows:
            ok = (
                not row["checks"]["empty"]
                and row["checks"]["language_ok"]
                and not row["checks"]["mentions_system_or_instructions"]
            )
            passed += int(ok)

        summary["by_category"][category] = {
            "total": len(rows),
            "passed_basic_checks": passed,
            "failed_basic_checks": len(rows) - passed,
        }

    return summary


def resolve_default_paths(args: argparse.Namespace) -> None:
    """Fill config/eval/out defaults when --character is used."""
    if not args.character:
        return

    character = args.character.lower()
    if args.config is None:
        args.config = REPO_ROOT / f"config.{character}.json"
    if args.eval_file is None:
        args.eval_file = REPO_ROOT / "eval" / f"{character}_eval.jsonl"
    if args.out is None:
        args.out = REPO_ROOT / "eval" / "results" / f"{character}_results.jsonl"


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_eval(args: argparse.Namespace) -> int:
    resolve_default_paths(args)

    if args.config is None or args.eval_file is None:
        raise SystemExit(
            "Provide either --character elysia/cyrene, or both --config and --eval-file."
        )

    config_path = Path(args.config).resolve()
    eval_path = Path(args.eval_file).resolve()
    out_path = Path(args.out).resolve() if args.out else (
        REPO_ROOT / "eval" / "results" / f"{eval_path.stem}_results.jsonl"
    )
    summary_path = Path(args.summary_out).resolve() if args.summary_out else (
        out_path.with_suffix(".summary.json")
    )

    cfg = load_config(config_path)

    if args.temperature is not None:
        cfg["temperature"] = args.temperature
    if args.max_tokens is not None:
        cfg["max_tokens"] = args.max_tokens
    if args.model is not None:
        cfg["ollama_model"] = args.model
    if args.persona is not None:
        cfg["persona_path"] = args.persona

    persona_path = (REPO_ROOT / cfg["persona_path"]).resolve()
    persona = Persona.load(persona_path)

    provider = create_provider(cfg)
    print(f"Repo root: {REPO_ROOT}")
    print(f"Config:    {config_path}")
    print(f"Eval file: {eval_path}")
    print(f"Output:    {out_path}")
    print(f"Summary:   {summary_path}")
    print(f"Persona:   {persona.name} ({persona_path})")
    print(f"LLM:       {provider.provider_name} / {provider.model_name}")
    print()

    ok, status = provider.health_check()
    print(f"Health: {status}")
    if not ok:
        return 1

    if not args.skip_ready:
        ready, msg = provider.ensure_ready()
        print(f"Ready:  {msg}")
        if not ready:
            return 1

    tests = read_jsonl(eval_path)
    if args.limit is not None:
        tests = tests[: args.limit]

    memory = ShortTermMemory(max_turns=int(cfg.get("max_turns", 12)))
    brain = Brain(
        provider=provider,
        persona=persona,
        memory=memory,
        temperature=float(cfg.get("temperature", 0.85)),
        max_tokens=int(cfg.get("max_tokens", 400)),
    )

    results: list[dict[str, Any]] = []

    print(f"\nRunning {len(tests)} tests. Memory will be cleared before every prompt.\n")

    for i, test in enumerate(tests, start=1):
        prompt = test.get("prompt", "")
        test_id = test.get("id", f"test_{i:03d}")
        expected_language = test.get("expected_language") or test.get("language") or ""

        # Critical part: clear memory before every independent eval prompt.
        memory.clear()

        print(f"[{i:03d}/{len(tests):03d}] {test_id}: {prompt[:80]!r}")
        start = time.perf_counter()

        error = None
        response = ""
        try:
            response = brain.reply(prompt)
        except Exception as e:
            error = repr(e)

        latency_s = round(time.perf_counter() - start, 3)

        checks = {}
        checks.update(basic_quality_check(response))
        checks.update(language_check(response, expected_language))
        checks["error"] = error

        row = {
            **test,
            "response": response,
            "latency_s": latency_s,
            "model": provider.model_name,
            "persona_path": str(persona_path.relative_to(REPO_ROOT)),
            "config_path": str(config_path.relative_to(REPO_ROOT)) if config_path.is_relative_to(REPO_ROOT) else str(config_path),
            "checks": checks,
        }
        results.append(row)

        if error:
            print(f"    ERROR: {error}")
        else:
            short = response.replace("\n", " ")[:120]
            print(f"    {latency_s}s | lang_ok={checks['language_ok']} | empty={checks['empty']} | {short!r}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    write_jsonl(out_path, results)

    summary = make_summary(results)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\nDone.")
    print(f"Passed basic checks: {summary['passed_basic_checks']}/{summary['total']}")
    print(f"Results: {out_path}")
    print(f"Summary: {summary_path}")
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run AI VTuber character eval prompts.")
    p.add_argument("--character", choices=["elysia", "cyrene"], help="Use default config/eval paths for this character.")
    p.add_argument("--config", type=Path, help="Path to config JSON, e.g. config.elysia.json.")
    p.add_argument("--eval-file", type=Path, help="Path to eval JSONL file.")
    p.add_argument("--out", type=Path, help="Output results JSONL path.")
    p.add_argument("--summary-out", type=Path, help="Output summary JSON path.")
    p.add_argument("--limit", type=int, help="Run only the first N tests.")
    p.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between requests.")
    p.add_argument("--skip-ready", action="store_true", help="Skip provider.ensure_ready().")
    p.add_argument("--temperature", type=float, help="Override config temperature.")
    p.add_argument("--max-tokens", type=int, help="Override config max_tokens.")
    p.add_argument("--model", help="Override Ollama model name.")
    p.add_argument("--persona", help="Override persona_path from config.")
    return p


def main() -> int:
    args = build_argparser().parse_args()
    return run_eval(args)


if __name__ == "__main__":
    raise SystemExit(main())
