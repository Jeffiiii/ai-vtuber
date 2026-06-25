# ai-vtuber

A Neuro-sama–style AI VTuber, built in stages. **Stage 1 is here and runnable today:**
a persona-driven, bilingual (English + 中文) text chatbot running on a **local** LLM via
Ollama. Voice, avatar, chat ingestion, memory, and autonomy come in later stages.

The LLM layer is adapted from the sibling **Conference** project's provider pattern
(`LLMProvider` interface + robust Ollama lifecycle management), so you can swap models
or add cloud backends with a one-line change.

---

## What works now (Stage 1)

- A **character** ("Aria" by default) defined in `persona/default.json` — identity,
  personality, speaking style, language rules, boundaries, and few-shot examples.
- A **conversation brain** that injects the persona + few-shot voice priming + rolling
  short-term memory, and **streams** replies token-by-token.
- A **robust local LLM provider**: auto-starts the Ollama server, auto-pulls the model
  on first run, warms it up so the first reply doesn't 503, and keeps it resident.
- **Bilingual**: replies in whatever language the viewer used (English or Chinese).

## Requirements

- **Python 3.10+**
- **[Ollama](https://ollama.com)** installed (you're downloading it now 👍)
- **RTX 4060 (8GB) + i9 + 32GB RAM** comfortably runs a quantized 7B model.

No `pip install` is needed for the core — Stage 1 uses only the Python standard library.
(`pytest` is only needed to run the tests.)

## Quickstart

```bash
# 1. (optional) create your own config
cp config.example.json config.json      # Windows: copy config.example.json config.json

# 2. start chatting — first run auto-downloads the model (~4-5 GB)
python -m aivtuber.cli
```

Then just type. Commands: `/reset` clears memory, `/quit` exits.

If you'd rather pull the model manually first:

```bash
ollama pull qwen2.5:7b-instruct
```

## Model choice (for your 8GB RTX 4060)

| Model | Notes |
|---|---|
| `qwen2.5:7b-instruct` *(default)* | Strong **English + Chinese**, fits 8GB at q4. Recommended. |
| `qwen2.5:3b-instruct` | Lighter/faster, still bilingual — good if you want lower latency. |
| `llama3.1:8b` | Excellent English, weaker Chinese. |

Change it in `config.json` (`ollama_model`) or via env var `AIVT_MODEL`.

## Make it *your* character

Edit `persona/default.json` (or copy it and point `persona_path` at the copy). The
`name`, `personality`, `speaking_style`, and `examples` fields do most of the work —
the examples especially lock in the voice. Point at a custom file with `AIVT_PERSONA`.

## Project layout

```
ai-vtuber/
├─ aivtuber/
│  ├─ llm/                 # LLMProvider interface + Ollama backend + factory
│  │  ├─ base.py           #   (adapted from Conference/conference/llm/base.py)
│  │  ├─ ollama_provider.py#   auto-start/pull/warm + streaming
│  │  └─ factory.py        #   add cloud providers here later
│  ├─ persona.py           # persona loader + system-prompt builder
│  ├─ brain.py             # persona + memory + LLM -> streaming reply
│  ├─ memory.py            # short-term (now) + long-term stub (Stage 4)
│  ├─ config.py            # defaults <- config.json <- env
│  ├─ cli.py               # interactive terminal chat  ← run this
│  └─ tts/                 # Stage 2 voice — interface stub only
├─ persona/default.json    # the character
├─ tests/                  # run without Ollama (provider is mocked)
├─ config.example.json
└─ requirements.txt
```

## Roadmap (where this is going)

1. **Stage 1 — text brain** ✅ *(this repo)*
2. **Stage 2 — voice + ears**: add TTS (Coqui XTTSv2, EN/ZH) in `aivtuber/tts/`;
   add STT — you can reuse Conference's ASR stack. Focus: real-time latency.
3. **Stage 3 — avatar + live**: Live2D in VTube Studio, OBS, Twitch/YouTube chat in.
4. **Stage 4 — memory + autonomy**: wire `LongTermMemory` to Conference's
   `semantic/` (embeddings + FAISS); add unprompted talking + vision.
5. **Stage 5 — polish/scale**: fine-tuning, moderation, performance.

See the roadmap & budget docs in the parent folder for the full plan.

## Reused from Conference

The `LLMProvider` abstraction and the Ollama lifecycle robustness (auto-start,
auto-pull, warm-up, keep-alive, 503 retry) come straight from the Conference
project's `conference/llm/` — battle-tested there, simplified here for an
English/Chinese persona and made dependency-free.
