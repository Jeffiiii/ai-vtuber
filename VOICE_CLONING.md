# Giving Elysia her own voice (XTTS voice cloning)

XTTS v2 can **clone a voice from one short reference clip**. Point the app at a
clean clip of Elysia and she'll speak (EN *and* ZH) in that timbre — on the
desktop app and on the website.

## 1. Get a good reference clip

The clip quality matters far more than its length. Aim for:

- **6–20 seconds** of a **single speaker** (Elysia only).
- **No background music, no sound effects, no overlapping voices.** This is the
  #1 thing — a clean dry voice clips beautifully; a clip with BGM clones the BGM too.
- A **calm, representative** speaking tone (normal talking, not shouting or singing).
- One language is enough — XTTS clones *timbre*, which carries across languages, so a
  clean Chinese line will also shape her English voice (and vice-versa).

A single clear voice line works better than a long noisy montage.

## 2. Clean it up (recommended)

Raw rips are often stereo, loud, or have a little silence/BGM. Normalize to a mono
24 kHz WAV and trim edges. With **ffmpeg** (install once: `winget install Gyan.FFmpeg`):

```
ffmpeg -i your_clip.wav -ac 1 -ar 24000 -af "silenceremove=start_periods=1:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse,loudnorm" voice/elysia_ref.wav
```

Or just convert without the fancy trimming:

```
ffmpeg -i your_clip.wav -ac 1 -ar 24000 voice/elysia_ref.wav
```

Put the result at `ai-vtuber/voice/elysia_ref.wav` (create the `voice/` folder).

## 3. Point the app at it

In `config.json`, set EITHER a single file:

```json
{ "xtts_speaker_wav": "voice/elysia_ref.wav" }
```

…or **a folder of clips** (recommended — see below):

```json
{ "xtts_speaker_wav": "voice/elysia" }
```

The backend prefers the clone over the built-in voice when the path exists, blends
**all `.wav` files** if it's a folder, and safely falls back to the built-in voice
if the path is missing.

Now:
- **Desktop:** `python -m aivtuber.orchestrator` → she speaks in the cloned voice.
- **Website:** run `python serve_tts.py` (in the same venv) → the site uses the same
  cloned voice instead of the browser's default. Hard-refresh the page; send a message.

## 4. Sounds creepy / only a little like her? (read this)

One short clip rarely captures a voice well — this is the usual cause. Fix it with
**multiple clean clips + a language match**, in roughly this priority:

1. **Use 3–6 clips, not one.** Make a `voice/elysia/` folder and drop in several
   clean **6–10 s** clips of her *talking* (different sentences, same calm tone).
   Point `xtts_speaker_wav` at the folder. XTTS blends them → far more stable and
   accurate. This is the single biggest improvement.
2. **Match the language.** A Chinese reference makes the best Chinese voice; an
   English reference the best English. If she'll mostly speak Chinese, use Chinese
   clips. Mixing in one clip of the other language helps that side too.
3. **Avoid in-game effects.** Lines with reverb, echo, battle SFX, or music clone
   those artifacts → that "creepy" sound. Prefer dry dialogue (story/voice-line rips
   without BGM).
4. **Keep it calm.** Shouting, crying, or singing clips produce weird prosody. Pick
   normal, expressive-but-steady talking.

### Then tune the knobs (in `config.json`)

If the *tone* still wobbles after better clips, adjust generation:

```json
{
  "xtts_temperature": 0.55,        // lower = steadier, less "creepy" (try 0.5–0.65)
  "xtts_repetition_penalty": 3.0,  // raise if she slurs or repeats syllables
  "xtts_speed": 1.0                // 0.9–1.1; tiny changes shift naturalness
}
```

Re-run `serve_tts.py` (or the orchestrator) after changing clips or knobs — the
model reloads the reference on restart. Change one thing at a time so you can hear
what helped.

## ⚠️ Licensing note (same as the Live2D model)

Cloning a game character's voice actor is fine for **private testing**, but for any
**public or monetized stream** you should use a **licensed or commissioned** voice
(or an original voice actor). Treat `elysia_ref.wav` as a development placeholder.
