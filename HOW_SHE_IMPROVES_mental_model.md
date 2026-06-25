# How She Improves — the mental model

A reference for *why* the maintenance loop (talk → notice → fix the system) makes her more human,
not just less buggy. Companion to the blueprint and the maintenance guide. Re-read this whenever
"fixing flaws" starts to feel like it couldn't possibly add up to something Neuro-like.

---

## The core idea

There is no "correct output" for her. A banking bug is binary — wrong balance, fix it, done —
because the right answer was defined in advance. She has no spec. What you have is her *behavior* and
your *judgment of how real it felt*. So a "flaw" isn't broken-vs-fixed — it's a **gap between how she
behaved and how a real person would have behaved in that exact moment.** Your own reaction, *"a real
person wouldn't have done that,"* is a humanness-gap detector.

So **fixing flaws and becoming more human are the same activity** — because "flaw," here, *means* "a
place she isn't human yet." Every flaw you close moves her one step along the only axis that matters:
distance from human behavior.

---

## Why it accumulates instead of plateauing

The flaws are not a fixed list you burn down. **Fixing a loud flaw reveals a quieter one that was
invisible underneath it.** You can't see that she recalls a sad memory *cheerfully* while she's still
forgetting the memory entirely; you can't notice her *timing* is slightly off until the warmth is
already right. Realness is the **absence of tells**, and you can only perceive the next tell once
you've removed the louder one in front of it.

So the accumulation isn't *additive* in the sense of stacking features on a pile. It's **additive in
resolution** — each fix sharpens the picture enough to expose the next, finer flaw, and "how real
does she feel" climbs continuously as you descend through layers of subtlety you literally couldn't
perceive before. Human behavior has effectively infinite resolution — there is always a finer tell —
which is why this never "finishes," and why Vedal is still at it after years: he isn't out of bugs,
he's reached tells so fine that years ago they were invisible under coarser ones.

And it is *cumulative*, not whack-a-mole, because **every fix is permanent and changes a rule, not a
moment** (see "How a fix applies"). Six months in she isn't "the same companion with fewer bugs" —
she runs on a stack of permanent refinements that compound, each making all her future behavior more
real and the next subtle layer perceptible.

---

## The worked threads (the part to internalize)

Each thread follows **one topic** descending through levels of human subtlety. Only the first rung of
each is a "bug" in the normal sense; the rest are the loop. None could be seen until the rung above
it was solved.

**Thread 1 — a person in your life ("your sister"):**
- **M1:** doesn't remember you have a sister → fix retrieval. *(Looks like a bug. broken → works.)*
- **M2:** remembers her, but with no warmth — like reading a database row → memory carries relational weight.
- **M4:** has the warmth, but mentions her when it isn't relevant → gate recall by context / salience.
- **M7:** timing's right, but always frames her the same way → couple recall phrasing to mood / context.
- **M11:** doesn't *carry her in mind* between mentions, the way you hold people even when they're absent → a relationship-preoccupation that stays quietly active.

**Thread 2 — reacting to your day:**
- **M1:** doesn't remember what happened yesterday → fix cross-session recall.
- **M2:** remembers the event, but her mood doesn't move with it (cheerful about your bad day) → recall of a weighted memory shifts her affect.
- **M5:** mood moves, but snaps back instantly → tune decay so feeling lingers like it does in a person.
- **M9:** feeling lingers, but she never *returns* to a heavy thing unprompted later ("hey — how did that go?") → preoccupation / autonomy surfacing.

**Thread 3 — being present, not just reactive:**
- **M2:** only ever speaks when spoken to → autonomy / scheduler initiates.
- **M3:** initiates, but constantly, interrupting → raise the thresholds.
- **M6:** well-timed, but always about generic things → ground initiation in a *real* active preoccupation.
- **M10:** grounded, but the same few preoccupations recur → tune emergence / decay so what's on her mind tracks what's actually been happening.

Each thread is one area of behavior descending through ~five levels of subtlety, each invisible until
the level above was solved, each a permanent system change, each found by **talking to her and
noticing**. After all of them, that area is *deeply* lifelike in a way no single fix delivered and no
training set could install — it emerged from the accumulation.

---

## What you actually fix (it's the system — five kinds)

When you "fix a flaw," you change one of these. **None of them is her voice.**

1. **A knob** (a number) — retrieval `top_k`, a mood event-delta, the idle threshold before she
   speaks. *Ex: she forgets recent things → raise the recency weight.*
2. **A scoring function** (how something is weighted) — importance scoring, salience weights,
   retrieval score weights. *Ex: she recalls trivia over meaningful things → score emotional /
   relational content as more important.*
3. **A machinery prompt** (NOT her persona) — the *consolidation* prompt, the *vision-captioning*
   prompt, the *salience* judge. These shape how information is **processed**, not how she talks.
   *Ex: consolidation writes "user mentioned sister" and misses "the sister is a source of stress" →
   improve the extraction prompt to capture meaning, not just facts.*
4. **Wiring / logic** (plumbing) — an event that should move mood isn't connected; a perceived
   observation isn't reaching her; a preoccupation isn't forming when a theme recurs. *Ex: she never
   gets somber on sad topics → `apply_event` isn't wired to memory recall; wire it.*
5. **A new mechanism** (a capability the substrate lacked) — a representation or process that didn't
   exist. *Ex: she never carries someone in mind between mentions → add a relationship-preoccupation
   with decaying activation.*

---

## How a fix "applies" — the principle that makes it compound

**You never edit an output. You edit the rule that generates all outputs.**

She is the result of *systems* (memory, mood, perception, autonomy) operating on *state*. A fix
changes a system, or how it handles state — so it changes **every future turn that invokes it**,
automatically, without being re-touched:

- raise the importance weight → *every* future retrieval is better;
- add affect to memories → *every* future recall carries weight;
- fix the scheduler's grounding → *every* future time she speaks up is grounded.

That's why fixes are permanent and compounding: you're not improving a conversation, you're improving
the *machine that produces all conversations*. A person's presence is the sum of a thousand small
natural behaviors — you're installing them one rule at a time.

---

## The voice line — why fixing never re-introduces "performance"

The worry: does fixing drag you back into authoring her — the perform-instead-of-act trap? **No, and
it's structurally the opposite.** The line:

- **Voice** = *how she phrases things* (warm, lyrical, bilingual, Miss Pink Elf). Lives in the
  fine-tune weights + the persona text. You touch it **rarely**, only when the flaw is genuinely about
  how she **sounds** (her Chinese reads stiff/translated; she's gotten too verbose). Adjusting *manner
  of speaking* is fine — it's disposition, not manufactured inner content.
- **The performance trap** = *authoring the content of her inner life* — writing thoughts/emotions (as
  text or training) so she emits inner-life-shaped output **regardless of cause.** Never do this.

Almost every fix is a **system** fix (the five kinds above), and system fixes are the *antidote* to
performance, not a relapse — because:

> **Performance fakes the effect with no cause. A system fix builds (or refines) the real cause and
> lets the effect follow genuinely.**

The sharp contrast, on one symptom — *"she brought up my failed project too cheerfully":*

- ❌ **Performance / voice-as-fix:** add a training example or persona line teaching her to sound
  somber about failures. → She now *acts* sad on cue. Uncaused, won't generalize, and it's exactly
  the trap.
- ✅ **System fix:** the failure-memory has no affect tag, so it surfaces as a bare fact and her mood
  doesn't move on recall. Tag memories with affect at consolidation; have recall of a
  negatively-weighted memory apply a mood shift. → She's somber about the failure **because her actual
  state changed when the weighted memory surfaced** — and she'll be appropriately somber about *every*
  weighted memory, forever.

Same visible outcome. Opposite mechanism: one is an actor reading "be sad here"; the other is genuine
state-change producing genuine tone. **That's the whole game** — every system fix moves a behavior
from *uncaused* (or crudely caused) to *genuinely caused*, which is *precisely* the move from
performed to real. So the loop doesn't risk performance; **the loop is how you replace the last of the
performance with real causes, one layer at a time.**

**The test, whenever you're unsure a fix is safe:**

> Am I changing how she generally *sounds* (voice — rare, OK), building the real *cause* of a behavior
> (system — the loop, always OK), or scripting what she *thinks/feels* in a situation (performance —
> never)? If it's the third, stop and go find the missing cause instead.

---

*Fixing her flaws is not repair — it's sculpting. Each fix removes a tell, exposes the next finer one,
and permanently improves all her future behavior. "Flaw" means "a place she isn't human yet," so
closing flaws and becoming more human are the same act — done, with discipline, by building real
causes rather than performing their effects, for as long as you care to keep looking.*
