# Run Elysia — complete setup & launch guide

This is the start-here guide. If you've never seen this project, follow it top to bottom and
you'll have friends chatting with Elysia on the website. No prior context needed.

---

## 0. What you're setting up (the pieces)

Elysia is an AI VTuber companion. There are a few moving parts; you don't need all of them:

| Piece | What it is | Where it runs | Needed for… |
|---|---|---|---|
| **Brain** (`serve_elysia.py`) | serves the fine-tuned model over HTTP | WSL (Linux on Windows), uses the GPU | everything |
| **Website chat** (`jeffi`) | the pretty public chat page (Live2D avatar, browser voice) | a static web host / your PC | **friends chatting** |
| **OLV** (`run_server.py`) | full desktop companion app (your own use) | Windows | your own deep sessions |
| **Voice (GSVI)** *(optional)* | higher-quality spoken voice | Windows + GPU | nicer TTS (website works without it via browser voice) |
| **Tunnel** (Tailscale) | makes a local service reachable from the internet | Windows | letting **remote** friends in |

**The three project folders** (already on this PC):
- `C:\Users\Leo12\Documents\ai-vtuber` — the brain + training + this guide. In WSL: `/mnt/c/Users/Leo12/Documents/ai-vtuber`.
- `C:\Users\Leo12\Documents\Open-LLM-VTuber` — the OLV companion app + the maintenance tools.
- `C:\Users\Leo12\Documents\jeffi` — the website (the chat page friends use).

> **Most common goal — "let my friends chat with her":** do **Part 1** (brain) + **Part 2**
> (make it reachable) + **Part 3** (website). Part 4 (OLV desktop) and Part 5 (GSVI voice) are
> optional.

---

## First-time only — install prerequisites

You need: **Windows 11**, an **NVIDIA GPU**, **WSL2 with Ubuntu**, **Python 3.10+**, and (for
remote friends) a free **Tailscale** account. One-time setup:

1. **The model.** The brain needs a merged model folder at
   `ai-vtuber/output/elysia-merged-v1voice`. If it's not there yet, build it once by following
   **`PHASE0_VOICE_RETRAIN.md`** (train → merge). If you already have it, skip this.

2. **Brain dependencies** (WSL, one time):
   ```bash
   python -m venv ~/.venv-train && source ~/.venv-train/bin/activate
   pip install torch --index-url https://download.pytorch.org/whl/cu124
   pip install -r /mnt/c/Users/Leo12/Documents/ai-vtuber/requirements-train.txt
   ```

3. **OLV dependencies** (only if you'll run the desktop app — Windows, in the OLV folder):
   `uv sync`  (or `pip install -r requirements.txt` inside your Python env).

4. **Tailscale** (only for remote friends): install from tailscale.com, sign in.
   *(cloudflared and free ngrok don't work behind the GFW here — Tailscale does.)*

---

## Part 1 — Start the brain (always needed)

Open a **WSL/Ubuntu** terminal:

```bash
source ~/.venv-train/bin/activate
cd /mnt/c/Users/Leo12/Documents/ai-vtuber
python serve_elysia.py \
  --model output/elysia-merged-v1voice \
  --host 127.0.0.1 --port 8000 \
  --reactive
```

Wait for two lines:
- `[reactive_brain] ON — memory=cache/web_memory, log=logs/reactive_turns_web`
- `Ready. GPU: NVIDIA GeForce RTX 4060 …` → `Serving on http://127.0.0.1:8000`

**What `--reactive` does:** gives the website chat real **memory + mood** and logs every turn
(so you can review it later). Leave it off only if you want a plain, memory-less brain.

**Quick test** (any terminal): you should get a short, in-character reply:
```bash
curl http://127.0.0.1:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi elysia"}],"stream":false}'
```

Leave this terminal open. The brain is now running on port **8000**.

---

## Part 2 — Make it reachable for friends (Tailscale)

Skip this if you're only testing on **your own PC** (then friends/you use
`http://localhost:8000` directly in Part 3).

For **remote friends**, expose port 8000 over HTTPS. New Windows PowerShell terminal:

```powershell
tailscale funnel 8000
```

It prints a public URL like `https://laptop-xxxx.tailNNNN.ts.net/`. **Copy it** — that's your
**brain URL**. (First run may print a link to enable Funnel in the Tailscale admin console; click
it, then re-run.) Leave this open. Stop public access anytime with `tailscale funnel 8000 off`.

> HTTPS matters: browsers only allow the microphone on https, and the public GitHub page (also
> https) can only call an https brain. Tailscale gives you https automatically.

---

## Part 3 — The website chat

The chat page is `jeffi`. Two ways to use it:

**Option A — test on your own PC** (no deploy). New PowerShell terminal:
```powershell
cd C:\Users\Leo12\Documents\jeffi
python -m http.server 5500
```
Open **http://localhost:5500/ui_kits/elysia-chat/** and **hard-refresh** (Ctrl+Shift+R).
It talks to `http://127.0.0.1:8000` automatically.

**Option B — share with friends** (public). One time, deploy the `jeffi` folder to GitHub Pages
(push the repo; Pages serves it at `https://<you>.github.io/...`). Then send friends this link,
pasting your **brain URL** from Part 2 after `?llm=`:
```
https://<you>.github.io/ui_kits/elysia-chat/?llm=https://laptop-xxxx.tailNNNN.ts.net
```
The page remembers the URL, so they can re-open `…/elysia-chat/` later without the `?llm=` part.

**Verify it's working:** the badge under the chat should turn green and read **`elysia-merged-v1voice`**
(connected to the real brain). Say "hi" — she replies in character, and her voice plays via the
browser. If the badge says **demo mode**, the page can't reach the brain (see Troubleshooting).

**Where the conversations go:** because the brain runs with `--reactive`, every turn is saved to
`ai-vtuber/logs/reactive_turns_web/<date>.jsonl` and per-visitor memory to
`ai-vtuber/cache/web_memory/`. That's what you review later (see `MAINTENANCE_READY.md`).

**That's it — friends can now chat with Elysia.** Parts 4–5 are optional.

---

## Part 4 — OLV desktop companion (your own use, optional)

OLV is the full app with the Live2D avatar for **your** deep sessions. It also uses the brain
(Part 1), so keep that running. Windows, in the OLV folder:

```powershell
cd C:\Users\Leo12\Documents\Open-LLM-VTuber
python run_server.py
```
Open the printed URL (default **http://localhost:12393**). Talk to her by text or mic.

**Let friends use OLV instead of the website** (isolated guest session — no access to your private
memory or screen):
```powershell
python run_server.py --guest        # prints "GUEST MODE on"
tailscale funnel 12393              # share the printed ts.net URL with friends
```
See **`GUEST_CHAT_SETUP.md`** for the full guest flow. *(Note: the website chat is usually the
better friend-facing surface — it has a working avatar on phones; OLV's avatar can be blank on
mobile.)*

---

## Part 5 — Higher-quality voice (GSVI, optional)

The website already speaks via the **browser's** built-in voice — you can skip this. For Elysia's
cloned GSVI voice, run two more services **before** opening the website:

```powershell
# 1) GSVI engine
cd C:\Users\Leo12\Documents\GPT-SoVITS-1007-cu124\GPT-SoVITS-1007-cu124
runtime\python.exe gsvi.py -p 8002          # wait: Uvicorn running on http://0.0.0.0:8002

# 2) voice proxy (ai-vtuber venv)
cd C:\Users\Leo12\Documents\ai-vtuber
.venv\Scripts\Activate.ps1
python serve_tts.py                          # wait: TTS serving on http://127.0.0.1:8020
```
Then add the voice tunnel + `&tts=` to the share link:
```powershell
tailscale funnel 8020
# link: https://<you>.github.io/ui_kits/elysia-chat/?llm=https://BRAIN.ts.net&tts=https://VOICE.ts.net
```

---

## Stopping everything

Press **Ctrl+C** in each terminal. To cut public access immediately, `tailscale funnel 8000 off`
(and `12393 off` / `8020 off` if used). The brain can stay running between sessions.

---

## Troubleshooting

- **Website says "demo mode" with servers up** — the page can't reach the brain.
  - *Local (Option A):* your `127.0.0.1:1080` system proxy is blocking localhost. Add
    `localhost;127.0.0.1;::1` to the Windows proxy bypass (Settings → Proxy → manual → exceptions),
    then hard-refresh.
  - *Remote (Option B):* make sure Part 2's `tailscale funnel 8000` is still running and you used
    its exact https URL after `?llm=`. **Always hard-refresh** after starting servers — the page
    only checks on load.
- **`[reactive_brain] OFF` at brain startup** — it couldn't find OLV's modules. Pass
  `--olv-src /mnt/c/Users/Leo12/Documents/Open-LLM-VTuber/src` to `serve_elysia.py`. (Without it,
  the chat still works but has no memory/mood.)
- **CUDA out of memory** — the brain (~6 GB) + GSVI (~2 GB) share the 8 GB GPU. Start one before
  the other, skip GSVI (use browser voice), or lower `--max_tokens`.
- **Avatar blank on a friend's phone** — known OLV-frontend quirk on mobile; the website chat's
  avatar works there. Chat + logging are unaffected.
- **Tunnel URL changed** — Tailscale quick URLs are stable per machine, but if it changes, just
  re-share the link with the new `?llm=` value.

---

## One-glance summary

| Goal | Run | Open / share |
|---|---|---|
| Friends chat (website) | brain `--reactive` → `tailscale funnel 8000` | `…github.io/ui_kits/elysia-chat/?llm=<brain-url>` |
| Test website locally | brain `--reactive` → `python -m http.server 5500` | `localhost:5500/ui_kits/elysia-chat/` |
| Your desktop companion | brain → `python run_server.py` | `localhost:12393` |
| Friends in OLV (guest) | brain → `run_server.py --guest` → `tailscale funnel 12393` | the ts.net URL |
