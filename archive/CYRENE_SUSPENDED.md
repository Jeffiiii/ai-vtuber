# Cyrene — development suspended (June 2026)

## Decision
Active development of **Cyrene (the assistant)** is **paused**. The project now focuses
solely on **Elysia (the VTuber)**, which is the real goal.

## Why
- The "in-character **and** genuinely useful assistant" goal is a fundamental tension on
  a small local model: pushing the persona reduces usefulness and vice-versa.
- A 7B–8B local model has an intelligence ceiling well below frontier models, so no amount
  of fine-tuning makes a local Cyrene as smart as a hosted frontier assistant.
- For real assistant work, using a frontier model directly is simply better value.

## Status of her files (kept, not deleted)
These remain in the repo and in git history, ready to revive at any time:
- `persona/cyrene.json` — her character + 60 bilingual examples (good training data).
- `config.cyrene.json` — her runtime preset.
- `scripts/posttrain/*cyrene*`, `eval/*cyrene*` — her eval/training scaffolding.

Nothing about Cyrene affects Elysia: the app loads whatever `config.json` points to, and
the test suite auto-selects an available persona (Elysia first).

## If you want to fully remove her from the working tree later
She stays in git history regardless, so this is safe:
```bash
git rm persona/cyrene.json config.cyrene.json
git commit -m "Archive Cyrene; focus on Elysia"
# restore anytime: git checkout <commit> -- persona/cyrene.json config.cyrene.json
```

## If you change your mind — the better revival path
Don't rebuild Cyrene as a local 7B assistant. Instead make her a **thin persona over a
frontier/cloud model** (add a cloud provider in `aivtuber/llm/factory.py`, point her
config's `llm_provider` at it). A large model holds a light persona *and* stays smart, so
the tension you felt mostly disappears. The persona JSON you already wrote works as-is.
