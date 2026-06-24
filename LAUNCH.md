# Launch checklist — run the whole Elysia stack

Four processes. Start them in this order. Each runs in its own terminal and stays open.

Ports: **8000** LLM brain · **8002** GSVI voice · **8020** voice proxy · **5500** website.

---

## 1. LLM brain (WSL — needs the GPU + trained model)

Open an Ubuntu/WSL terminal:

```bash
source ~/.venv-train/bin/activate
python /mnt/c/Users/Leo12/Documents/ai-vtuber/serve_elysia.py \
  --model /mnt/c/Users/Leo12/Documents/ai-vtuber/elysia-merged
```
Wait for: `Ready. GPU: NVIDIA GeForce RTX 4060 Laptop GPU` → `Serving on http://127.0.0.1:8000`.

## 2. GSVI voice (Windows PowerShell)

```powershell
cd C:\Users\Leo12\Documents\GPT-SoVITS-1007-cu124\GPT-SoVITS-1007-cu124
runtime\python.exe gsvi.py -p 8002
```
Wait for: `Uvicorn running on http://0.0.0.0:8002`. (Loads the 爱莉希雅 v4 model.)

## 3. Voice proxy (Windows PowerShell — ai-vtuber venv)

```powershell
cd C:\Users\Leo12\Documents\ai-vtuber
.venv\Scripts\Activate.ps1
python serve_tts.py
```
Wait for: `Ready on gsvi (爱莉希雅)` → `TTS serving on http://127.0.0.1:8020`.

## 4. Website (Windows PowerShell — jeffi)

```powershell
cd C:\Users\Leo12\Documents\jeffi
python -m http.server 5500
```
Open **http://localhost:5500/ui_kits/elysia-chat/** (NOT the github.io URL — the public
site can't reach your local servers). Hard-refresh (Ctrl+Shift+R) after all servers are up.

Badge should read green `elysia-merged` (brain) and `Elysia (GSVI · local)` (voice).

---

## Desktop VTuber instead of the website

Once 1 + 2 are up, run the orchestrator (Windows, ai-vtuber venv) instead of 3 + 4:

```powershell
cd C:\Users\Leo12\Documents\ai-vtuber
.venv\Scripts\Activate.ps1
python -m aivtuber.orchestrator              # console chat + web avatar + GSVI voice
python -m aivtuber.orchestrator --platform bilibili   # read your Bilibili room
```
Web avatar (for OBS) at http://127.0.0.1:8010.

---

## Gotchas

- **System proxy:** if the website shows `demo mode` / `browser TTS` even with servers up,
  your `127.0.0.1:1080` proxy is blocking localhost. Add `localhost;127.0.0.1;::1` to the
  proxy bypass (Windows → Proxy → manual → exceptions), then hard-refresh.
- **Page only checks servers on load** — always hard-refresh after starting the servers.
- **VRAM:** the LLM (~6 GB) + GSVI (~2 GB) share the 8 GB GPU. If GSVI or the LLM throws
  CUDA OOM, start one before the other, or lower the LLM `max_tokens`.
- **Voice speed:** first line loads the model once (~5-9 s); after that it's cached and fast.
  `gsvi_sample_steps` (config.json) trades speed vs quality (8 fast / 16 nicer).
