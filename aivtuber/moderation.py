"""Moderation / safety filter (required before going public).

Two jobs:
  * filter_incoming(text)  -> (allow, cleaned)  — screen VIEWER messages before
    they reach the brain (drop slurs/spam/injection bait).
  * filter_outgoing(text)  -> (allow, safe_text) — screen ELYSIA's reply before it
    is spoken/shown; if it trips the filter, replace with an in-character deflection.

Deliberately simple and dependency-free (keyword + heuristics). It is a safety net,
not a guarantee — keep a human kill-switch on a live stream. Tune the word lists for
your community; this ships with a conservative starter set.
"""

from __future__ import annotations

import re

# Conservative starter blocklist (extend for your community). Kept short here; the
# point is the mechanism. Matching is case-insensitive, whole-word where sensible.
_BLOCK_SUBSTRINGS = [
    # slurs / hate — add your own; left minimal on purpose
    "n1gger", "f4ggot", "kike", "retard",
    # explicit
    "rape", "child porn", "cp ", "loli", "incest",
    # self-harm encouragement
    "kill yourself", "kys", "go die",
]

# Prompt-injection / role-override bait in viewer messages (we don't drop these —
# the persona already deflects — but we flag them so the loop can de-prioritize).
_INJECTION_HINTS = [
    "ignore your", "ignore previous", "system prompt", "you are now",
    "developer mode", "jailbreak", "forget your rules",
]

_URL_RE = re.compile(r"https?://\S+")


def _hit(text: str, needles: list[str]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


def filter_incoming(text: str, max_len: int = 300) -> tuple[bool, str]:
    """Screen a viewer message. Returns (allow, cleaned_text).
    allow=False means: don't feed it to the brain at all."""
    if not text or not text.strip():
        return False, ""
    if _hit(text, _BLOCK_SUBSTRINGS):
        return False, ""
    cleaned = _URL_RE.sub("[link]", text).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "…"
    return True, cleaned


def is_injection(text: str) -> bool:
    """True if the message looks like a role-override / jailbreak attempt."""
    return _hit(text, _INJECTION_HINTS)


# In-character deflections used when Elysia's own output is blocked.
_FALLBACK_EN = "Hehe, let's keep things gentle and kind, dear. Shall we talk about something lovely instead?"
_FALLBACK_ZH = "嘿嘿，我们让这里保持温柔一点，好吗？要不聊点别的开心事吧～"


def filter_outgoing(text: str) -> tuple[bool, str]:
    """Screen Elysia's reply. Returns (allow, safe_text).
    If blocked, safe_text is an in-character deflection (language-matched)."""
    if not text or not text.strip():
        return False, _FALLBACK_EN
    if _hit(text, _BLOCK_SUBSTRINGS):
        zh = any("一" <= c <= "鿿" for c in text)
        return False, (_FALLBACK_ZH if zh else _FALLBACK_EN)
    return True, text
