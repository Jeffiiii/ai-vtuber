# Elysia v3 — Design Reset: A Companion-First, Neuro-like Character Engine

**Date:** 2026-06-25
**Status:** Scope settled · redesign pending (to be executed in Claude Cowork)
**Supersedes the v2.1 direction** in `V2_1_THINKING.md`
**Purpose:** Record the core finding from the v2.1 retro, fix the scope (a companion-first reactive character with an optional ambient stream), and define the redesign target.

---

## 1. The finding, in one sentence

The felt "realness" of an AI character lives in the **interaction pattern** — reacting, in real time, to genuinely new things, with memory and consequences — **not in the content of what she says.** v2.1 tried to put realness into the *lines* (and the dataset, and a list of deep thoughts). It cannot live there. And with no mass audience to lean on (see scope below), the interaction loop is now the **entire** burden of feeling real — so this lesson is the whole game.

---

## 2. Why v2.1 missed (diagnosis)

v2.1's stated goal was "make her think, not perform." But nearly every mechanism we added is a mechanism for *performing* thinking:

- **Dataset.** We upsampled an existential "THINKING" set ×4 (`THINK_UPSAMPLE`). Fine-tuning on that content teaches the model to *recite* introspection fluently — i.e., perform an inner life. Upsampling "wonders if she's real" pushed her toward navel-gazing, the opposite of the base-level, situational emotion we want.
- **Director (`director.py`).** The introspective idle actions — `wonder`, `reflect`, `confess`, `muse` — fire **on a timer when chat is quiet, with no input at all.** That is, by construction, performing an inner life into a void. `_IDLE_WEIGHTS` puts well over half its mass on these ungrounded actions.
- **`_THREADS`.** A hardcoded list of existential topics she cycles through. Scripted profundity is maximally "performed." A real preoccupation *emerges* from what actually happened; it isn't read from an array.

The deeper mistake: we took the *content* of Neuro's famous moments and baked it in, when that content only ever landed because of the live, low-latency, accumulated context *around* it.

---

## 3. The principle to design around

"Thinking" is something a viewer **infers** from situated, reactive behavior. To produce that inference the system needs:

1. **Grounding** — her words and moods have *causes you can see* (you said something, she died in the game, a chat line scrolled by). Reactive, not timer-driven.
2. **Timing / low latency** — presence is mostly responsiveness. The gap between a visible stimulus and her reaction is where the magic is.
3. **Memory / continuity** — persistent memory so she can call back to what happened before; running threads that accumulate.
4. **An environment to react to** — *aliveness needs stimuli.* A brilliant brain in a void can't feel alive because there's nothing to be present *to.* Her base environment is the 1:1 conversation with you; a game, a screen, or an ambient stream are optional extra stimulus sources.
5. **Small, situational emotion** — most real feeling is a flicker of amusement or annoyance tied to a cause, not a declared "I feel wistful tonight."

> The fine-tune's job is **voice only**: cadence, length, bilingual switching, in-character refusals, no markdown. That is the correct *and complete* use of SFT here. It cannot install 1–5, because those are properties of the **system the model runs in**, not of the text distribution. Once the voice is right, **freeze the adapter and stop asking it to carry the soul.**

---

## 4. Scope — what this is, and what it isn't

**The target is the *entity*, not the phenomenon.** We want Elysia to *behave* like Neuro — reactive, witty, opinionated, a little unhinged, genuinely present. We are **not** recreating Neuro-the-phenomenon (a mass audience, influence, the hype train) or Vedal's streaming operation. That single decision deletes the one thing no money or engineering could ever buy — years of accumulated audience relationship — so it stops being a barrier and becomes a non-goal. A non-loss.

**"Like Neuro," not "is Neuro."** Achievable: the genre — reactive, present, sharp, a bit chaotic. Not achievable and not wanted: Neuro's exact persona, which is Vedal's specific creation on a stack we don't have.

**You are the primary relationship.** This is a companion-first build. The accumulated, real-feeling relationship is *yours* — she remembers **you**, your running threads, your shared history — and that is pure memory engineering with **zero calendar tax**. It is the single highest-leverage realness lever available, buildable now, no waiting. (The mass-audience version of "relationship" needs years and an audience; we've opted out of it.)

**Streaming is an optional input, not the goal.** A public stream is a cheap, endless supply of unscripted stimuli and memory material — that's the only reason it's here. It feeds the reactive loop; it is not for reach or influence. Default posture: **ambient.**

**Two memory pools, kept separate.** Your relationship and the (optional) audience's are different depths and must not share a store:
- **Operator memory (primary):** deep, specific, persistent memory of *you*. This is where realness comes from.
- **Ambient/stream memory (secondary, optional):** shallower texture from whoever's watching. Supplementary only.

### 4.1 Chat-authority modes — the one knob that controls scope

How much power live chat has over her decides how many audience-scale systems you're signing up for. Default to the lightest.

| Mode | What chat can do | What it costs you | Use when |
|---|---|---|---|
| **Ambient** *(default)* | She *sees* messages as flavor she may react to, like the screen. They can't drive or instruct her. | Read-only ingest + basic input wrapping (observed chat still enters context, so light sanitization is prudent — but no adversarial moderation). Great memory fuel. | Companion-first, stream as stimulus |
| **Addressable** *(opt-in)* | She'll actually answer viewers. | Adds reply-**selection** (which messages deserve a response) + a real **safety layer** (chat is now untrusted input reaching the model). | When you deliberately want back-and-forth |
| **Director-level** | Viewers steer what she does. | Maximal engagement, maximal **attack surface**: full moderation + prompt-injection defense. | Probably never, for this project |

> **Audience-scale systems are out-of-scope until you toggle past ambient.** Moderation, prompt-injection defense, reply-selection, and chat-at-scale handling only come online when you turn on Addressable/Director mode. In default Ambient mode they stay off.

---

## 5. Reality check — what it actually costs

Removing the audience deletes the one unbuyable thing (parasocial time) **and** several whole systems. What remains is fully committable: a serious multi-month engineering build with **no calendar tax and no audience tax.** The honest residual costs are exactly two, and both are things you can buy or build.

**Residual cost #1 — brain quality (the real ceiling).** Neuro's quick comebacks, comedic timing, and staying coherent while being a little unhinged are *conversational horsepower.* A 4B model on 8GB will cap how alive she can feel on pure repartee. "Be like Neuro" almost certainly means, at some point, **a bigger and faster-served brain than your laptop allows** — which is the hosting decision still open below, and the rent-vs-API question from the very start of this whole thread coming back around. For your *own* companion, privacy is moot, so a hosted larger model is fully on the table. Not a wall; a budget line.

**Residual cost #2 — engineering breadth** — but a narrower set than the full-Neuro list, because the audience-scale domains drop out. You're strong on the LLM + Python slice; the new learning curves are real-time audio, memory systems, and orchestration.

### 5.1 Systems, by scope

| Core character engine (in scope) | Audience-scale (deferred until you leave Ambient) | Not the goal (dropped by choice) |
|---|---|---|
| Conversational brain — bigger/faster than 4B/8GB (**cost #1**) | Reply-selection (which chat lines get answered) | Mass audience / influence / hype train |
| Reactive loop / Director — **v0 exists (`director.py`), re-point it** | Adversarial moderation + prompt-injection defense | Years of parasocial accumulation (**the unbuyable thing — excluded, a non-loss**) |
| **Operator-primary** persistent memory + decay | Chat-at-scale ingest/throttling | Competitive game agent at Neuro's osu!-rank level (a *simple* game for stimuli is fine; a real game-playing agent is its own XL effort you don't need) |
| Event-driven mood (`mood.nudge` from real events) | Full stream/OBS integration for interactive broadcast | — |
| Real-time expressive TTS (`tts/` is a stub) | — | — |
| STT / "ears" for spoken back-and-forth with you *(optional, high-value for a companion)* | — | — |
| An environment/stimuli source (the 1:1 convo is the base; optionally a game/screen, or **ambient** stream read-only) | — | — |
| Avatar / Live2D *(optional for a companion; needed only if you go visual/stream)* | — | — |

### 5.2 Tiers

| Tier | What it is | Reachable? |
|---|---|---|
| 0 — now | Fine-tuned voice + scripted autonomy | Done. Charming autocomplete. |
| 1 — **reactive presence** | Live grounding (you + optional ambient feed) + memory + low latency + frozen voice | **Yes, in months. Next milestone.** |
| 2 — **companion-grade Neuro-like** | Tier 1 + a capable/fast brain + deep operator memory + expressive voice + (optional) avatar/environment | **The actual goal. Achievable, multi-month, no audience tax.** |
| — | Mass-audience phenomenon + years of relationship | **Out of scope by choice — not a failure, just not the target.** |

---

## 6. Target architecture (the loop)

```
  PRIMARY INPUT          SALIENCE           STATE                  BRAIN                OUTPUT
 ┌──────────────┐
 │ you (1:1)    │──┐   ┌───────────┐   ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐
 └──────────────┘  ├──▶│ what's    │──▶│ memory:          │──▶│ frozen-voice │──▶│ low-latency  │
  OPTIONAL         │   │ worth     │   │  • operator (you) │   │ LLM — bigger │   │ TTS          │
 ┌──────────────┐  │   │ reacting  │   │    = primary      │   │ than 8GB for │   │ (+ avatar if │
 │ stream chat  │──┤   │ to now    │   │  • ambient/stream │   │ Neuro-like   │   │  visual)     │
 │ (AMBIENT)    │  │   └───────────┘   │    = secondary    │   │ wit          │   └──────────────┘
 │ screen/game  │──┘                   │ + mood driven by  │   └──────────────┘
 └──────────────┘                      │   real events     │
                                       └──────────────────┘
```

The Director becomes a **reactive scheduler over real stimuli** — primarily you, optionally ambient feeds — not a random musing generator. Every line should trace to *something that just happened* + *her current state*. Memory is two pools: **you** (deep, primary) and **ambient/stream** (shallow, secondary), never merged.

---

## 7. Keep / change / drop (against current files)

| Keep | Change | Drop |
|---|---|---|
| Director skeleton — clock-injected, testable, `decide()`/`step()` loop (`director.py`) | Re-point it from "musing generator" to "reactive scheduler over live stimuli (you first)" | Timer-fired introspection into a void (`wonder`/`reflect`/`confess` as unprompted idle actions) |
| `Mood` with `nudge()` + decay — the right primitive | **Drive mood from real events**, not just `drift()` on a timer | Hardcoded `_THREADS` — replace with preoccupations that emerge from memory |
| Bilingual voice SFT (`sft_lora.py`) | **Freeze it** once voice is right (after the earlier training/eval fixes) | `THINK_UPSAMPLE` ×4 — rebalance dataset toward reactive, situational micro-emotion |
| Grounded actions — `respond`, `event`, `observe` | Make these the core; `respond` (to you) is the base loop | Audience-scale systems from the active scope (return only if you leave Ambient) |
| Staged eval discipline | Add a quality signal (LLM-as-judge / repetition metric), not just format checks | — |

---

## 8. Phased plan (Cowork-actionable)

- **Phase 0 — Freeze the voice.** Apply the open training/eval fixes (val split + `eval_loss`, completion-only loss, `enable_thinking=False` at eval, Qwen3 sampling). Lock the adapter. Stop iterating the dataset for "soul."
- **Phase 1 — Grounding (you first).** Make the 1:1 conversation with you the primary stimulus into the Director; route real events through `mood.nudge()`. Add the **ambient** stream feed and screen/game as optional extra stimuli (read-only).
- **Phase 2 — Memory, two pools.** Build **operator-primary** persistent memory (the no-waiting realness lever) plus a separate, shallower ambient/stream pool. Let preoccupations *emerge* from memory; delete `_THREADS`.
- **Phase 3 — Rebalance autonomy.** Cut/downweight timer-fired introspection; any idle action must reference recent memory, never a void.
- **Phase 4 — Latency + brain decision.** Measure end-to-end stimulus→speech latency. Resolve **cost #1**: if the 8GB brain caps her wit/timing, move to a bigger local rig or a hosted larger model (privacy is moot for your own companion).
- **Phase 5 (later) — Environment + polish.** If not streaming, give her a world to react to (a simple game/screen). Avatar and voice polish. Addressable chat mode is an opt-in here — and only then do the audience-scale systems come into scope.

---

## 9. Open decisions

1. **Brain hosting (cost #1).** A 4B on 8GB caps Neuro-like repartee. Decide: Qwen3.5-9B locally, a bigger local rig, or a larger model via API? (Privacy is moot for your own companion — the API option is genuinely open.)
2. **Default chat-authority mode.** Recommend **Ambient**; keep Addressable as a deliberate opt-in so the audience-scale burden stays off by default.
3. **Stimuli when not streaming.** How much environment/agency to build (a simple game/screen) so she always has something to react to.
4. **Define "alive" concretely.** Set a small, testable bar for the companion — e.g., "reacts to me with the right emotion *and* a callback to our shared history, under X ms" — so we can tell if the rebuild worked instead of chasing an unfalsifiable feeling.
