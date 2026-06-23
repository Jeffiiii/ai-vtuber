"""Emotion tagging (Stage 3) — map a reply to an expression label.

A cheap bilingual (EN/ZH) heuristic that turns Elysia's reply into one of a small
set of emotions. The live loop sends that label to the avatar (VTube Studio) to
trigger the matching expression hotkey.

This is intentionally simple and dependency-free. Later you can swap in an
LLM-tagged emotion (ask the model to prefix a tag) for finer control.
"""

from __future__ import annotations

# Order matters: earlier emotions win when multiple match.
EMOTIONS = ["surprised", "sad", "shy", "playful", "happy", "neutral"]

_CUES = {
    "surprised": ["?!", "！？", "?！", "wow", "whoa", "oh!", "哎呀", "诶", "欸", "啊咧", "what?"],
    "sad": ["sorry", "i'm sorry", "im sorry", "rough", "hurts", "lonely", "miss you",
            "对不起", "抱歉", "难过", "唔", "辛苦", "心疼", "别担心"],
    "shy": ["blush", "embarrass", "shy", "//", "害羞", "脸红", "disc", "don't look"],
    "playful": ["hehe", "tease", "~", "wink", "♪", "嘻嘻", "嗯哼", "坏", "调皮", "偷偷"],
    "happy": ["yay", "love", "wonderful", "beautiful", "glad", "welcome", "thank",
              "开心", "喜欢", "欢迎", "谢谢", "太好", "可爱", "棒", "美好"],
}


def detect_emotion(text: str) -> str:
    """Return one emotion label from EMOTIONS for the given reply text."""
    if not text:
        return "neutral"
    low = text.lower()
    for emo in EMOTIONS:
        if emo in ("happy", "neutral"):
            continue  # checked last / default
        for cue in _CUES.get(emo, []):
            if cue in low:
                return emo
    # happy is the gentle default for Elysia if any positive cue, else neutral
    for cue in _CUES["happy"]:
        if cue in low:
            return "happy"
    return "neutral"


def expression_hotkey(emotion: str, mapping: dict) -> str | None:
    """Map an emotion label to the VTube Studio hotkey name from config.
    `mapping` is config['avatar_expressions'] (emotion -> hotkey name)."""
    return (mapping or {}).get(emotion)
