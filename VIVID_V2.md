# Making Elysia vivid — the v2 dataset + retrain

The v1 model reads like a polite chatbot because its training data was deliberately
terse ("keep replies short"). v2 fixes that: a looser, mood-aware system prompt + a
batch of longer, wittier, reactive lines, with **mood tags** so the Director's energy
picks how lively she is (tender → warm → playful → hyper).

## 1. Build the dataset

```bash
python scripts/add_vivid_examples.py
# -> data/elysia_train_v2.jsonl
```
It re-emits every v1 pair under the new system prompt (her default register) and adds
the vivid, mood-tagged examples, **upsampled x3** (see `UPSAMPLE` in the script) so the
lively register carries weight in the short LoRA run.

Tune it: edit `VIVID` (add your own lines), `MOOD_NOTES`, or `UPSAMPLE`, then re-run.

## 2. Retrain (QLoRA, WSL, ~10-15 min on the 4060)

```bash
source ~/.venv-train/bin/activate
cd /mnt/c/Users/Leo12/Documents/ai-vtuber

# smoke test first (a few steps, makes sure it runs):
python train/sft_lora.py --data data/elysia_train_v2.jsonl --out output/lora-elysia-v2 --smoke

# full run:
python train/sft_lora.py --data data/elysia_train_v2.jsonl --out output/lora-elysia-v2 --epochs 3
```

## 3. Merge + serve the v2 model

Merge the adapter into a standalone model (same step as v1 — see TRAINING_GUIDE.md),
e.g. to `output/elysia-merged-v2`, then point the server at it:

```bash
python serve_elysia.py --model /mnt/c/Users/Leo12/Documents/ai-vtuber/output/elysia-merged-v2
```
(Or overwrite `elysia-merged` once you're happy with v2.)

## 4. Let the Director drive the mood

The Director already injects a mood note each tick; v2 was trained against those exact
`[Mood: ...]` notes, so as her energy rises she gets longer, livelier, and more playful,
and as it falls she goes soft and tender. Tune the feel in `config.json`:

- `director_start_energy` (0-1) — where she starts.
- `director_idle_seconds` — how soon she talks unprompted.

## 5. Sanity-check the vibe

After serving v2, run the eval or just chat:
```bash
python scripts/run_character_eval.py     # if set up for v2
python -m aivtuber.autonomous            # watch her talk on her own
```
You want: still unmistakably Elysia (elegant, tender underneath), but now she riffs,
teases, calls back, and reacts — and her length/energy visibly shift with her mood.

## Notes

- Keep an eye on length: if she gets *too* rambly, lower `UPSAMPLE` to 2 or trim
  `max_tokens` in config. If still too terse, raise `UPSAMPLE` or add more vivid lines.
- The website chat (`ElysiaBrain.jsx`) has its own copy of the persona prompt; it was
  also loosened to match, so the browser chat feels consistent with the desktop.
