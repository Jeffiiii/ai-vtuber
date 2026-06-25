# Operations & Maintenance Guide — Reactive Companion

**What this is.** The runbook for *after* the blueprint is built. The blueprint builds the substrate;
this keeps it running and makes it get better over time. Consult it by lookup, not linear reading.

**Companion to:** `INTEGRATION_BLUEPRINT_open_llm_vtuber.md` (the architecture) and
`V3_DIRECTION_reactive_presence.md` (the why). All component and knob names below refer to the
blueprint.

**Who does what** — every task is tagged:
- **[You]** — Jeff: runs her (using her *is* the work), makes the "does she feel alive?" judgment,
  flags off-moments, sets priorities, owns the brain-upgrade cost decision.
- **[Cowork]** — builds/maintains the instrumentation, parses logs, runs the probe harness, implements
  tuning changes, runs hygiene scripts, does migrations and regression tests.
- **[Both]** — review and decide together.

**The one rule that governs everything:** when she feels off, you fix the **substrate**, never her
**output**. If you ever find yourself writing what she should say, adding a "thread," or prompting
"be more thoughtful," stop — that's the regression to the authored paradigm. See §0.

---

## 0. The prime directive — the off-moment protocol

This is the loop that drives *all* improvement. Run it every time she feels wrong.

1. **[You] Name the dimension.** Which felt off: memory (recall), mood (affect), timing (autonomy),
   perception (reaction to the world), or voice/brain (the reply itself)? Flag the moment (§1) so the
   exact state is captured.
2. **[Cowork] Pull the turn log** for the flagged moment(s). Look at the *real state* at that turn:
   what was retrieved, what the mood was, what fired the scheduler, what was perceived.
3. **[Both] Diagnose which component produced the bad output** — not "the reply was bad," but "the
   reply was bad *because* retrieval surfaced nothing / mood was flat / it fired with no real trigger
   / vision misread the screen / the model itself can't reason here."
4. **[Cowork] Fix that component** — turn a knob (§3, §4), fix a wiring, or improve a *system* prompt
   (consolidation, vision captioning). Change **one thing**.
5. **[Cowork] Validate** against the golden set (§7) before trusting it. **[You]** confirm by feel.

**Never** fix an off-moment by editing her lines, adding authored content, or telling the model to
perform. The **only** thing you ever shape at the output layer is *voice* (how she phrases), and only
via the voice training / persona disposition — never in-the-moment cognition or emotion. If a fix
looks like "make her say X," it's wrong; find the component that should have produced the right thing
on its own.

---

## 1. Instrumentation to build first (you cannot maintain what you cannot see)

**[Cowork] builds these immediately after P4/P5, before serious tuning.** Everything else in this
guide depends on them.

**1.1 Per-turn structured log** (JSONL, one line per turn — the spine of all monitoring):

```
{ ts, turn_id,
  input:   { source, from_name, text, lang },
  percept: { observation, source, age_s } | null,         # E
  memory:  { retrieved:[{id,kind,pool,score,rel,rec,imp}], used_in_reply:bool,
             written:[{id,kind,importance,merged_into?,superseded?}] },   # B
  mood:    { before:{v,a}, events_applied:[kind], after:{v,a}, attachment },  # C
  preoccupations: [{id,text,activation}],                  # B.7
  scheduler: { tick, decision, trigger_id?, reason },      # D
  reply:   { text, lang, expression },                     # output
  latency: { first_sentence_ms, full_ms, retrieval_ms, consolidation_ms_async },
  flagged: false }                                         # set by the off-moment flag (1.2)
```

**1.2 The "feels-off" flag** [Cowork builds, You use] — a one-keystroke / one-command way for you to
mark the *current or just-finished* turn as off, optionally with a one-word reason
(`forgot` / `dredged` / `flat` / `wrong-time` / `misread` / `bland` / `lang`). This is the single most
valuable signal you produce — it ties your subjective read to the exact captured state. Use it
liberally and in the moment.

**1.3 Probe / eval harness** [Cowork] — scripted scenarios runnable on demand, one per component
(memory recall, mood response, autonomy timing, language match, perception accuracy) plus the
**golden set** (§7). Reuse your existing `eval/` + `scripts/posttrain/` rig as the base; these probes
test the *running system*, not just the model.

**1.4 Memory inspector** [Cowork] — a CLI that dumps the store: top-N by importance and by access,
all preoccupations + activations, suspected duplicates (high pairwise similarity), suspected
contradictions, the operator profile, and per-pool counts. You run this during monthly audits.

**1.5 Weekly summary generator** [Cowork] — rolls the turn log into metrics (§ tracking the curve)
so you see trends, not just snapshots.

---

## 2. The maintenance cadence

| Cadence | Tasks | Who |
|---|---|---|
| **Every session** (~2 min) | Smoke check: services up, she replies in character, latency sane, language correct. Watch for obvious breaks; **flag** anything off. | [You] |
| **Each active-use day** | Skim flagged moments; jot a one-line note on anything that felt wrong (the running feels-off log builds itself from 1.2). | [You], parsed by [Cowork] |
| **Weekly** (~30–60 min) | Run the probe harness + golden set; generate the weekly summary; review flags + metrics together; pick **1–3** tuning changes and apply+validate; back up the memory DB; quick ambient-pool prune. | [Cowork] runs, [Both] decide |
| **Monthly** (~1–2 hr) | Full memory audit (1.4): contradiction sweep, profile-drift review, prune; review the brain-upgrade trigger (§6); review resource trends (disk, VRAM headroom, latency percentiles); re-baseline the golden set if her stable behavior has legitimately shifted. | [Both] |
| **Event-driven** | After *any* config/code change → regression test before trusting (§7). On a *persistent* one-dimension off-feel → the §0 protocol in depth. On brain ceiling → §6. | [Cowork] |

Rule of thumb: **change little and often.** Most weeks = 1–3 small knob turns, each validated. Big
swings make it impossible to tell what helped.

---

## 3. What to monitor, per subsystem (symptom → cause → fix)

For each subsystem: the signals to watch, what healthy looks like, and a symptom→fix table. Fixes
reference knobs catalogued in §4.

### 3.1 Memory [B]

**Watch:** retrieval hit usage (was a retrieved memory actually used?), retrieval scores, what
consolidation wrote, per-pool store size, contradiction/dedup events.
**Healthy:** relevant shared facts surface *when context warrants*; she doesn't dredge irrelevant old
items; no stale/contradicted facts appear; the store grows slowly and stays clean.

| Symptom | Likely cause | Fix |
|---|---|---|
| Forgets something she should know | retrieval recall too low, or it was never written | Raise `top_k`; lower `relevance_threshold`; raise `w_rec`/`w_imp`. **First check the log** — if it's not in `written`, the consolidation pass missed it → improve the extraction prompt or lower its importance bar. |
| Dredges irrelevant old memories | precision too low / over-retrieval | Lower `top_k`; raise `relevance_threshold`; lower `w_rec` (old stuff floating up). |
| Repeats the same memory too often | runaway `access_count` boost | Reduce the on-retrieval recency bump; cap repeat-surfacing; dedup. |
| "Remembers" wrong / contradictory facts | contradiction handling failing | Audit `superseded_by` (1.4); fix the consolidation contradiction step; manually supersede the stale item. |
| Replies slow + context bloated | memory token budget blown | Tighten `mem_token_budget`; lower `top_k`; summarize retrieved items before injecting. |
| Store full of junk/dupes over time | consolidation writing low-value items / weak dedup | Tighten the extraction prompt; raise the importance floor for writes; run dedup (§5); raise the dedup similarity threshold. |
| Recall feels generic / not *about you* | operator-profile digest stale or thin | Review profile drift (§5); check the LLM profile-refresh cadence (`due_for_update`). |

### 3.2 Mood [C]

**Watch:** the valence/arousal trace over time, which events fired and their deltas, attachment.
**Healthy:** mood *moves when real events happen* and decays back; shows in expression + word choice;
not flat, not wild, not stuck.

| Symptom | Likely cause | Fix |
|---|---|---|
| Mood never moves / flat | event deltas too small, or `apply_event` not wired to real outcomes | Check event wiring first (log shows empty `events_applied`); raise `EVENT_AFFECT_MAP` deltas. |
| Mood swings wildly | deltas too big or decay too slow | Lower deltas; speed `mood_decay`. |
| Mood gets stuck | decay-to-baseline too slow / wrong baseline | Tune `mood_decay`, `baseline_v/a`. |
| Mood doesn't *show* | expression mapping or note not reflecting state | Check `expression()` mapping → Live2D; confirm the tone note is injected and derived from real state. |
| Feels *performed* again (old trap) | a note/mood injected that the state didn't earn | Ensure the note derives only from genuinely-caused state; if mood is drifting randomly, that's the bug — events must cause it. |
| Attachment grows too fast/slow | increment off | Tune the per-interaction `attachment` step. |

### 3.3 Autonomy [D]

**Watch:** scheduler decisions (fire/no-fire, trigger, reason), idle gaps, preoccupation activations.
**Healthy:** she speaks up at appropriate moments about *genuinely active* things; neither silent for
ages nor constantly butting in; initiations feel grounded.

| Symptom | Likely cause | Fix |
|---|---|---|
| Never initiates | thresholds too high, or no preoccupations forming | Lower `idle_seconds`, `arousal_gate`, `activation_gate`; **check** preoccupations are being created (consolidation theme detection) — if none form, she has nothing to initiate about. |
| Initiates too much / interrupts | thresholds too low / tick too fast | Raise `idle_seconds`, `arousal_gate`, `activation_gate`; slow `tick_seconds`. |
| Initiates about nothing / generic | grounding broken — firing without a real trigger | Ensure `_should_initiate` returns a *specific* preoccupation/event and only fires on one; never a generic fallback. |
| Always the same preoccupation | activation not decaying or one dominating | Tune `preoccupation_decay`/`boost`; cap max activation; ensure decay runs each tick. |
| Reacts to ambient chat it should ignore | salience threshold too low | Raise `salience_threshold`; reweight salience features. |
| Wrong-language autonomous lines | language policy | Check the default-language policy for autonomous vs reply paths. |

### 3.4 Perception [E]

**Watch:** vision observations (captions) + their accuracy, cadence, freshness/age, latency; chat/event
intake; salience decisions.
**Healthy:** she reacts to real on-screen events accurately and promptly; no hallucinating about the
screen; reactions are to *current* state.

| Symptom | Likely cause | Fix |
|---|---|---|
| Reacts to the screen wrongly / hallucinates | VLM caption quality | Improve the captioning prompt; lower how much the agent trusts/volunteers screen detail; use a better/larger VLM (cost). |
| Ignores screen events | vision cadence too slow, observations not feeding the agent, or salience dropping them | Raise vision cadence (watch VRAM/latency); verify `_percept` reaches `_build_messages`; lower salience bar for perceived events. |
| Comments on stale screen state | observation freshness | Timestamp + expire observations (`percept.age_s`); drop stale ones before injecting. |
| Vision lags / overheats GPU | cadence too high / VLM too heavy for 8GB | Throttle cadence; run vision on CPU or a tiny VLM; time-share GPU (§8). |

### 3.5 Voice / model [A]

**Watch:** reply coherence, in-character-ness, language match, latency (first-sentence + full),
thinking-leak (`<think>` escaping), repetition.
**Healthy:** warm, in-character, correct-language replies; no performed introspection; acceptable
latency; no loops.

| Symptom | Likely cause | Fix |
|---|---|---|
| Replies bland/short *despite* working systems | **brain ceiling** (the 4B can't reason richly here) | This is the §6 upgrade signal — **not** a prompt to "be deeper." First rule out sampling (`temperature`/`top_p`) and that you trained on **v1 voice** data; if systems are dialed and it's still flat, upgrade the brain. |
| Performed introspection creeping back | thinking training/prompt reintroduced | Confirm the served model is **v1-voice-only** and the system prompt is voice-only; remove any thinking-mode prompt. |
| Language mismatch | sampling / training balance / policy | Check the language policy; check EN/ZH balance in voice data. |
| Latency high | context too big, model spilling to CPU (VRAM), KV cache type, segmentation | Tighten `mem_token_budget`/`top_k`; verify full GPU offload (the silent-CPU-offload trap); `OLLAMA_KV_CACHE_TYPE=q8_0`; check `faster_first_response`. |
| Repetition / loops | temp too low (Qwen3 quirk), no penalty | Raise `temperature` toward 0.7; add repetition/presence penalty. |

### 3.6 Operational health [§8]

**Watch:** each service up/down, VRAM headroom, RAM, memory-DB disk growth, crash/restart, latency
percentiles. See §8 for the budget and procedures.

---

## 4. Tuning-knob reference (single lookup table)

Defaults are starting points — *tune by symptom*, change one at a time, validate.

| Knob | Component | Affects | Turn it when |
|---|---|---|---|
| `top_k` | B retrieval | how many memories surface | forgets (↑) / dredges (↓) |
| `relevance_threshold` | B retrieval | min similarity to surface | dredges (↑) / forgets (↓) |
| `w_rel` / `w_rec` / `w_imp` | B retrieval | relevance vs recency vs importance balance | old stuff floats (↓`w_rec`) / forgets important (↑`w_imp`) |
| `mem_token_budget` | B assembly | context spent on memory | latency/bloat (↓) |
| `importance_floor` (write) | B consolidation | what gets stored | junk store (↑) / forgets (↓) |
| `dedup_similarity` | B write | merge vs keep separate | dupes (↓ to merge more) |
| forgetting thresholds | B.8 | when items prune/demote | store bloat (tighten) |
| `EVENT_AFFECT_MAP` deltas | C | how much events move mood | flat (↑) / wild (↓) |
| `mood_decay`, `baseline_v/a` | C | how fast mood returns | stuck (faster) / too volatile (slower) |
| `attachment` step | C | relationship-warmth growth rate | grows wrong-speed |
| `idle_seconds` | D | quiet before she may speak | silent (↓) / butts in (↑) |
| `arousal_gate`, `activation_gate` | D | state needed to initiate | silent (↓) / too chatty (↑) |
| `tick_seconds` | D | how often she considers speaking | too chatty (↑) |
| `preoccupation_decay` / `boost` | B.7/D | how long a thought stays active | fixates (faster decay) / never recurs (↑ boost) |
| `salience_threshold` + weights | D/E | which ambient input warrants reaction | over-reacts (↑) / misses (↓) |
| vision cadence | E | how often she perceives the screen | misses events (↑) / lags/OOM (↓) |
| observation TTL | E | how long a percept stays valid | stale comments (↓) |
| `temperature` / `top_p` / `top_k` (sampling) | A | reply liveliness vs coherence | bland (↑temp) / loose/repetitive (↓temp + penalty) |
| `OLLAMA_KV_CACHE_TYPE`, ctx size | A | VRAM + latency | OOM/spill (q8_0, ctx ≤8K) |

**[Cowork] keep all of these in a single versioned config**, and keep a **tuning changelog**
(date · knob · old→new · symptom · observed effect) so you can revert and learn.

---

## 5. Memory hygiene (the living data)

The store is the one component that *rots* if untended (and *deepens* if tended — it's your free
realness lever). **[Cowork] runs; [You] reviews the profile.**

- **Weekly:** back up the DB (copy the sqlite + index, timestamped). Prune the **ambient** pool
  aggressively (low-importance, old, unused).
- **Monthly (audit, via 1.4):**
  - **Contradiction sweep** — list items about the same entity/attribute; supersede stale ones.
  - **Dedup** — merge near-duplicates the live dedup missed; raise `dedup_similarity` if many.
  - **Profile-drift review [You]** — read the operator profile; the LLM rewrites it over time and can
    drift, flatten, or invent. Correct it if it's wrong about you. This is the one place you *edit
    memory directly* — and it's editing *facts*, not *behavior*, so it's allowed.
  - **Prune the operator pool gently** — only true junk; never lose real shared history.
- **On embedder change:** re-embed and re-index the whole store (vectors from a different model aren't
  comparable). Treat this as a migration with a backup + golden-set check.
- **Disk:** memory grows slowly but unboundedly; watch the trend (§8). Forgetting (B.8) should keep it
  near-flat — if it climbs steadily, forgetting is too gentle.

---

## 6. The brain-upgrade decision & procedure

The single biggest multiplier — and where real cost enters. Don't do it reflexively; do it when the
**brain is provably the binding constraint.**

**Trigger (the distinguishing diagnostic):** the systems are *dialed* — memory recalls well, mood
tracks events, autonomy is well-timed, perception is accurate — **and reactions are still flat,
shallow, or miss nuance.** That residual flatness, after the substrate is good, is the model's
reasoning ceiling. (If a system is still broken, fix the system first — don't mask it with a bigger
model.)

**Procedure** (it's a plugin, so mostly config + revalidate — **[Cowork]** mechanics, **[You]** cost
call):
1. Stand up the new brain: a larger local model (rented GPU) **or** an API model via OLV's
   `openai_compatible` backend.
2. Point the StatelessLLM config at it; **keep the current model as a fallback** (config flag).
3. Run the golden set + a **side-by-side feel test** [You] on real interactions.
4. Watch **cost and latency** alongside quality — both matter at the higher tiers.
5. Flip if clearly better; keep the fallback reversible.

**The voice tradeoff to weigh [Both]:** your fine-tuned *voice* lives in the 4B's weights. A non-tuned
API/large model is smarter but **loses Elysia's voice** → you'd need heavier persona prompting (weaker)
or to re-establish the voice on the new base (fine-tune it, if feasible). So the upgrade is a real
choice between *sharper reasoning* and *owned voice* — sometimes the answer is "keep the tuned 4B for
voice-critical, route hard reasoning to a bigger model," a split worth prototyping before committing.

---

## 7. Regression safety (don't break what works)

**[Cowork] enforces. Every change passes this before it's trusted.**

- **Golden set** — a fixed list of inputs/scenarios with expected *properties* (not exact text):
  e.g. "recalls that the operator's cat is Mochi," "replies in ZH to ZH," "does not dredge unrelated
  memories," "mood rises on praise," "initiates within N s of a real active preoccupation,"
  "reacts correctly to `player died` on screen." Run before+after every change.
- **Version the config** (git the conf + tuning params + system/consolidation/vision prompts).
- **Snapshot the memory DB before any risky change** (migrations, forgetting/dedup threshold changes,
  embedder swap).
- **Change one thing at a time**, validate, record in the tuning changelog.
- **Keep the model swap reversible** (the fallback flag from §6).

If a change passes the golden set but **[You]** feel it regressed something subtle, trust the feel —
add that scenario to the golden set so the metric catches it next time.

---

## 8. Resource & operational health (the 8GB reality)

**The hard constraint:** the voice model (Qwen3-4B Q4 + KV at ≤8K) already takes roughly the majority
of 8GB. A real VLM (vision), Whisper (STT), and GPU-TTS **cannot all also sit on the GPU** at once.

**Allocation strategy (until the brain moves off-box):**
- Voice model: GPU, full offload (verify no CPU spill — the silent latency killer).
- Vision VLM: **CPU or a tiny model, throttled** (it runs intermittently, so it can be slower);
  or time-share the GPU (load on demand). Don't let it OOM the voice model.
- STT/TTS: CPU if needed; OLV's lighter backends help.
- Embedder: tiny, fits anywhere.

**Monitor [Cowork], surface trends weekly:**

| Signal | Healthy | If not |
|---|---|---|
| VRAM headroom | model loaded with margin; **no OOM**, no CPU spill | move vision/STT/TTS to CPU; shrink ctx; throttle vision; (eventually) rent GPU |
| RAM | stable | check leaks; cap buffers |
| Memory-DB disk | near-flat (forgetting working) | tighten forgetting; prune |
| Latency p50/p95 (first-sentence + full) | first sentence snappy | see §3.5 latency row |
| Service uptime | model / OLV / vision / embedder all up | restart procedure below |

**[Cowork] build a health-check script** that pings each service (model `/health`, OLV ws, vision,
embedder) and a one-command restart for each. **[You]** run the health check at session start (§2).
Keep logs in a known path; rotate them.

The clean exits from the VRAM squeeze are (a) move perception/voice-IO models to CPU, (b) the
**brain-upgrade** (§6) — renting GPU or going API frees the local box entirely. The squeeze is also a
real input to *when* the upgrade is worth it.

---

## Tracking the curve (are we actually improving?)

**[Cowork] weekly summary (1.5); [Both] review monthly trend.** Watch these *over time* — the point of
the whole architecture is that they should trend the right way as you tune, use her, and upgrade:

- **Golden-set pass rate** — should rise then hold; a drop = a regression.
- **Retrieval hit rate** (retrieved-and-used / turns where recall was relevant) — up = memory landing.
- **Misfire rate** (flagged moments / turns) — down = fewer breaks.
- **Initiation appropriateness** (your weekly read of a sample of her initiations) — up.
- **Mood variance** (does it actually move with events, not flat/not wild) — in a healthy band.
- **Latency p95** — stable/down.
- **Memory depth** — store size + profile richness in the operator pool (this should *grow with use*;
  it's the lever that improves for free).

If these are flat or up and she *feels* more alive, the curve is going up. If you're working hard and
they're flat, you're likely either (a) re-authoring (§0) instead of fixing the substrate, or (b) at
the brain ceiling (§6).

---

## Quick reference — checklists

**Session start [You]:** health check passes · she replies in character · language correct · latency
sane · flag anything off.

**Weekly [Cowork→Both]:** run probes + golden set · generate summary · review flags+trends ·
apply 1–3 validated knob turns · back up DB · prune ambient · log changes.

**Monthly [Both]:** memory audit (contradictions, dedup, profile drift, prune) · brain-upgrade trigger
review · resource trends · re-baseline golden set if needed.

**After any change [Cowork]:** snapshot DB if risky · golden set before+after · one change · record in
tuning changelog · keep it reversible.

**On off-moment [Both]:** name the dimension · pull the turn log · diagnose the *component* · fix the
substrate (never the output) · validate.

---

*Maintenance here is gardening, not construction: run her, watch where the generation breaks, and
strengthen the component that broke. The systems compound and memory deepens with use — so steady,
small, substrate-level tending is what makes her more alive over time. The day you're tempted to fix
her by writing her lines is the day to re-read §0.*
