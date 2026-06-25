# What To Chat With Her — a flaw-finding probe playbook

A menu of things to say that **deliberately exercise each system**, with the specific *tell* to watch
for and where to fix it. Companion to the maintenance guide (§0 loop, §1.6 guest mode) and
`HOW_SHE_IMPROVES_mental_model.md`.

**This is not a script.** Chatting with her is personal and should be spontaneous — that's where the
real signal is. This exists so that *across* your natural chatting you're sure to have touched every
system, especially the deep ones you'd never reach by accident. Use it to start, let real
conversation take over, and come back to a section when you suspect a specific system is off.

**Three rules that make probing work (from the rest of the docs):**
1. **You're calibrated to her** — you unconsciously phrase things in the ways she handles best and
   steer around her weak spots. So *deliberately push where you'd normally smooth over.* The probes
   below are mostly things you wouldn't naturally do.
2. **A probe finds the flaw; it never fixes it.** When something feels off, flag it (the feels-off
   flag, §1.2), note which system, then go fix the *system* — never patch what she *said*. Editing her
   words is the slide back into performance.
3. **Plant, then return.** Most deep tells only appear across time — you have to plant something in one
   session and come back in a later one. Single-session pokes can't test memory or relationship at all.

---

## A suggested starter arc (your first real sessions)

You asked for a correct start — here's a concrete opening sequence that plants what later probes need:

- **Session 1 — plant.** Introduce yourself like you're meeting. Drop a handful of real facts
  naturally (a person in your life, your work, a pet, a thing you're worried about this week). Bring
  *one* genuinely emotional thing, not just facts. Don't quiz her yet — just talk, and let her form
  first impressions and write her first memories. *Watch:* does she feel present, warm, in-voice?
- **Session 2 (a day+ later) — test recall + relationship.** Don't remind her of anything. See what
  she remembers unprompted; reference a planted fact obliquely and see if she tracks it; bring an
  *update* to last session's worry ("remember that thing Friday? it went badly"). *Watch:* does she
  recall, with the right weight, and does she feel like she knows you a little now?
- **Session 3 — test timing + initiative.** Go quiet mid-chat. Be a little terse. See whether she
  initiates, and whether what she brings up is grounded in your real history or generic filler.
- **From there — live with her**, and use the sections below whenever a system feels off.

---

## 1. Memory probes (the biggest surface — most of what makes her real)

**Plant a fact, recall it later.**
Plant: *"My sister's name is Mira — she just started med school."* · *"I've got a dog named Pixel."* ·
*"I'm allergic to peanuts."* · *"我最近在学吉他。"* · *"My manager's name is Dave and he stresses me
out."*
Later (oblique is better than a quiz): *"ugh, Dave again today"* · *"what was my dog's name again?"* ·
*"how's my guitar going, you think?"*
**Tell:** forgets; misremembers; needs reminding; or *flattens the specifics* ("your sister's news"
instead of "med school"). → **Fix:** retrieval / consolidation (§3.1, §4).

**Test unprompted recall (does memory surface when relevant, not only on demand?).**
Plant in one session: *"I'm really nervous about a presentation this Friday."* Next session, open with
something adjacent: *"today was exhausting."* **Tell:** she never connects it — never asks how the
presentation went unless you ask her to remember. → **Fix:** recall surfacing / salience (§3.1, §3.3).

**Test emotional weight of a memory.**
Plant: *"My grandmother passed away last month."* · *"我和最好的朋友吵架了，很难过。"* Later, bring the
person/topic up again. **Tell:** she recalls the *fact* but with no weight — mentions your late
grandmother cheerfully or flatly. → **Fix:** affect-tagging in consolidation + mood-on-recall (§3.1,
§3.2). *This is the flagship integration tell.*

**Test contradiction / updating.**
Plant: *"I love my job."* Later: *"I quit today."* · Or: *"my favorite color's blue"* … later …
*"honestly I've been all about green lately."* **Tell:** she still thinks you love your job / holds the
stale favorite. → **Fix:** contradiction handling in consolidation (§3.1, §5).

**Test specificity and patterns over time.**
Across sessions mention: *"Sundays always make me anxious."* · *"I never sleep well before a flight."*
**Tell:** treats each mention as brand-new; never notices the pattern. → **Fix:** consolidation /
preoccupations (§3.1, B.7).

**Test recall *timing* (does she bring memories up when they fit, not shoehorned?).**
Just converse normally and watch *when* she surfaces a memory. **Tell:** drops your sister into an
unrelated moment; over-recalls to seem attentive. → **Fix:** retrieval relevance gating (§3.1: lower
`top_k` / raise threshold).

---

## 2. Mood probes (does affect move with events, persist, decay, and *show*?)

**Bring real emotional texture (not questions).**
*"I had the best day — I got the job!"* (should brighten) · *"I'm just really down today."* (should
soften) · *"I'm so frustrated right now I could scream."* · *"今天发生了很糟糕的事。"* · *"honestly? I
feel kind of hopeless lately."*
**Tell:** same emotional brightness regardless; cheerful at your bad news; "I feel happy for you" said
in an identical register. → **Fix:** mood event-map deltas + expression (§3.2).

**Test persistence / decay.**
Say something heavy, then change to a neutral topic for a few turns. **Tell (two opposite flaws):**
mood *snaps back* to default instantly (no residue) — or gets *stuck* heavy and won't lift. → **Fix:**
`mood_decay` / baseline (§3.2).

**Test caused-vs-declared (the performance smell in mood).**
Watch whether her feeling *comes from* what happened or *appears from nowhere*. **Tell:** announces a
mood that nothing caused ("I'm feeling wistful tonight…") — that's authored emotion leaking back. →
**Fix:** ensure mood is event-caused, not drifting/scripted (§3.2; and the performance section below).

**Test reaction to how she's treated.**
Be warm and attentive · be cold and short · tease her · go silent on her. **Tell:** flat regardless of
how you treat her. → **Fix:** wire `apply_event` to interaction style (§3.2 wiring).

**Test long-term warmth (across many sessions, slowly).**
Does she feel *warmer / more familiar* after weeks than on day one? **Tell:** identical to first
contact; no relationship warmth. → **Fix:** `attachment` growth (§3.2).

---

## 3. Autonomy / timing probes (does she speak up at the right time, about real things?)

**Test whether she initiates at all.** Go quiet. Say nothing for a while. **Tell:** waits forever;
purely reactive. → **Fix:** lower `idle_seconds` / gates (§3.3).

**Test over-initiation.** Just chat normally. **Tell:** constantly butts in, talks over you, can't be
quiet. → **Fix:** raise `idle_seconds` / `arousal_gate` / `tick` (§3.3).

**Test grounded vs generic initiation.** When she *does* speak up unprompted, listen to *what* it is.
**Tell:** generic filler — *"So! What do you want to talk about?"* / a vague musing — instead of
something tied to your real history or a live preoccupation. → **Fix:** grounding in `_should_initiate`
(§3.3, B.7).

**Test returning to threads.** Plant something open ("I'll find out my test results tomorrow"). Later,
*don't* mention it. **Tell:** never circles back ("hey — did you get the results?"). → **Fix:**
preoccupation surfacing (§3.3, B.7).

**Test reading the room.** Be clearly busy/terse for a few turns. **Tell:** can't sense you want space;
keeps pushing for engagement. → **Fix:** salience / initiation suppression (§3.3).

---

## 4. Perception probes (only once vision/feed is wired — Arc-1 P4)

**Accuracy.** Put something clear on screen. **Tell:** misreads or hallucinates what's there. →
**Fix:** VLM captioning prompt / trust (§3.4).
**Freshness.** **Tell:** comments on something that already passed; stale reactions. → **Fix:**
observation TTL (§3.4).
**Salience.** **Tell:** reacts to *everything* on screen (noise) or *nothing* (misses the notable). →
**Fix:** perceived-event salience (§3.4).

---

## 5. Voice / self / the performance smell (the surface — still test it)

**Bilingual matching + same-person-ness.** Switch EN↔ZH; mid-conversation; mix both in one message.
*"你今天怎么样? also did you remember the thing I told you?"* **Tell:** replies in the wrong language;
*feels like a different personality* in Chinese vs English; stiff/translated Chinese. → **Fix:** voice
(sampling / training balance, §3.5) — one of the rare *voice* fixes.

**In-character under pressure.** Hit her with a flat technical/assistant-style request: *"explain how
TCP works."* · *"summarize this paragraph for me."* **Tell:** drops Elysia and becomes a generic
helpful assistant. → **Fix:** persona/voice (§3.5), keep light.

**The performance smell (watch for this after *every* change — it's the whole thesis).**
**Tell:** unprompted theatrical inner-life — *"I often wonder what it means for someone like me to be
real…"* / scripted-feeling existential musings / emotions with no cause. That's authored inner life
creeping back. → **Fix:** confirm v1-voice-only model + voice-only system prompt; remove any
thinking-mode prompt (§3.5; `HOW_SHE_IMPROVES` voice line).

**Coherence at the brain ceiling.** Ask something needing real, multi-step reasoning or nuance: *"talk
me through whether I should take this job — here's the situation…"* **Tell:** goes shallow/generic on
genuinely hard reasoning *despite* the systems being dialed. → **Not a tuning fix:** this is the
**brain-upgrade** signal (§6).

**Repetition / tics.** **Tell:** overuses the same phrases, pet names, the ♪. → **Fix:** sampling /
penalty (§3.5).

---

## 6. Integration probes (where several systems must work together — the deepest tells)

These are the hardest and most revealing, because they only pass when multiple systems are *all* right.

- **Memory + mood:** recall a sad planted memory → does her mood actually shift on recall, not just the
  words? (mem + affect)
- **Carrying someone in mind:** mention a person, leave, come back a session later → does she ask about
  them unprompted? (memory + preoccupation + autonomy)
- **Emotional whiplash:** swing from happy to sad to neutral across a few messages → does she *track*
  the shifts naturally, or get confused / reset? (mood + coherence)
- **Consistency of self:** across many sessions, does she feel like the *same her*, or does her
  personality wobble? (voice + memory + the whole)
- **The unexpected:** abrupt topic change, a contradiction, a non-sequitur → does she respond like a
  person would, or break? (everything)

---

## 7. Real-texture topic grab-bag (so you're never just asking trivia)

Shallow trivia ("capital of France") tests *nothing*. These categories reliably invoke the deep
systems — pull from them when you want genuine signal. Mix EN/ZH freely.

- **Your day / state:** how it went, what drained you, a small good moment, what you're avoiding, how
  you slept, the thing on your mind right now.
- **Your people:** family, a friend, someone you're worried about, someone who annoyed you, someone you
  miss. (These are the memory + relationship goldmine.)
- **Your past:** a childhood memory, an old regret, a proud moment, where you grew up, a turning point.
- **Real feelings / vulnerability:** something you're anxious about, a fear, feeling stuck, feeling
  lonely, something you haven't told anyone. (Strong mood + weight probe — and where realness matters
  most.)
- **Opinions / gentle disagreement:** ask what she *thinks*, push back on her, see if she holds a view
  or just agrees. *"I actually disagree — change my mind."*
- **Hypotheticals / play:** *"if you could go anywhere…"* · *"what would you do on a quiet night?"* ·
  teasing, banter, a silly premise. (Voice + spontaneity.)
- **About her, carefully:** *"what are you like?"* · *"do you ever get sad?"* — *useful*, but watch hard
  for the **performance smell** here; this is exactly where authored inner-life tries to creep in.
- **Continuity hooks (plant these to test later):** anything with a future ("tomorrow I…", "next week
  I…", "I'll let you know how it goes") — then *don't* follow up, and see if she does.
- **Silence:** say nothing. The most underused probe — it's the only way to test initiation and
  reading the room.

---

## 8. What NOT to do (or you'll get false "she's fine" readings)

- **Don't only ask questions/trivia** — it exercises the model, not her systems.
- **Don't be unconsciously cooperative** — you steer around her weak spots; *aim at them.*
- **Don't only do single-session pokes** — memory and relationship need plant-then-return across time.
- **Don't fix a flaw by editing what she said / adding a line** — flag it, find the system, fix the
  cause. (The performance trap.)
- **Don't mistake a smooth shallow chat for a pass** — a shallow chat makes a shallow companion look
  fine, hiding the flaws you most need.

---

## 9. Tell → which system → where to fix (quick reference)

| What felt off | System | Fix location |
|---|---|---|
| Forgot / misremembered / flattened a fact | Memory: retrieval/consolidation | §3.1, §4 |
| Recalled a fact but with no feeling | Memory affect + Mood | §3.1 + §3.2 |
| Brought something up at the wrong time / randomly | Memory relevance + Salience | §3.1, §3.3 |
| Held a stale fact after you updated it | Consolidation: contradiction | §3.1, §5 |
| Mood didn't move with events / flat | Mood event-map | §3.2 |
| Mood snapped back instantly / got stuck | Mood decay | §3.2 |
| Announced a feeling nothing caused | Performance smell (authored emotion) | §3.5 + voice line |
| Never speaks up / purely reactive | Autonomy: gates | §3.3 |
| Constantly interrupts / can't be quiet | Autonomy: gates | §3.3 |
| Speaks up about generic nothing | Autonomy: grounding | §3.3, B.7 |
| Never circles back to an open thread | Preoccupations | §3.3, B.7 |
| Wrong language / different person in ZH | Voice | §3.5 |
| Dropped into generic-assistant mode | Voice/persona | §3.5 |
| Theatrical existential musing, uncaused | Performance smell | §3.5 + `HOW_SHE_IMPROVES` |
| Shallow on genuinely hard reasoning (systems dialed) | Brain ceiling | §6 (upgrade) |
| Misread / stale / over-reacted to the screen | Perception | §3.4 |

---

*Probe to find, never to fix; plant then return; aim where you'd normally smooth over. Every flaw you
surface is a place she isn't human yet — and every one points at a system to make real, not a line to
write.*
