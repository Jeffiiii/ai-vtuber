# Long-term memory — Elysia remembers regulars

She now keeps a small, durable profile of each viewer **across sessions**, so a returning
regular gets greeted like someone she knows.

## How it works

- Store: `memory/longterm.json` (one entry per viewer). Each holds: `name` (if they reveal
  it), a one-line `summary`, a few `facts`, an `interactions` count, and a short `recent`
  buffer of turns. No external deps, no embeddings — just JSON.
- **Recall:** when a viewer speaks, the orchestrator calls `brain.set_speaker(user)`, and the
  brain injects a line like *"You remember this viewer, whom you know as Mika (12 past
  messages together). A cheerful regular who loves rhythm games…"* into the system prompt.
  She's told to let it color her tone, not recite it.
- **Refresh:** every `longterm_update_every` messages from that viewer (default 4), the brain
  asks the LLM — in a background thread, so it never delays speaking — to fold the recent
  chat into the profile (name, durable facts, summary). Small talk is dropped.
- Autonomous lines (muses/observations) do **not** pull a specific viewer's memory.

## Config (config.json)

```json
{
  "longterm_enabled": true,
  "longterm_path": "memory/longterm.json",
  "longterm_update_every": 4
}
```

## Try it

Run the orchestrator and chat (console viewer is `you`, so the profile builds for `you`;
on Bilibili each danmaku's username gets its own profile):

```
python -m aivtuber.orchestrator --no-voice
# tell her your name + an interest, chat a few lines, then /quit
# run it again and greet her — she should remember.
```

Watch `memory/longterm.json` fill in after a few of your messages.

## Manage it

- **Inspect/edit:** open `memory/longterm.json` — it's human-readable; tweak a summary or
  delete a fact by hand if she picked up something wrong.
- **Forget one viewer:** delete their object from the JSON.
- **Wipe all memory:** delete the file (it's recreated empty).
- **Turn it off:** set `"longterm_enabled": false`.

## Notes / limits

- Currently desktop/orchestrator only (the public website calls the LLM directly and has no
  server-side memory yet). If you want the website to remember too, that needs a small
  memory service behind `serve_elysia` — easy to add later.
- Multi-viewer attribution is "best effort": memory is recalled for the most recent speaker.
  Fine for one active chatter or a calm room; very busy chat could occasionally cross wires.
- The profile updater uses your local LLM, so it costs a little GPU every few messages
  (runs in the background, off the speaking path).
