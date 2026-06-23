# Training Guide — Fine-tuning Elysia (WSL2 + QLoRA on your RTX 4060)

A complete, copy-paste guide from a fresh Windows machine to a fine-tuned Elysia
model served through Ollama. Written for an RTX 4060 (8 GB) + Qwen3.

**The big picture:** you'll set up a Linux environment (WSL2), train a small LoRA
adapter on `data/elysia_train.jsonl`, check it beats your baseline, then merge it
and serve it in your app. Budget ~1 hour of setup + a few hours of (mostly hands-off)
training.

> Why WSL2: the 4-bit trainer (`bitsandbytes`) is far smoother on Linux than native
> Windows. Your app and Ollama still run on Windows — only training lives in WSL2.

---

## Step 0 — Prerequisites (on Windows)

1. **Windows 10 (22H2) or Windows 11.**
2. **Update your NVIDIA driver** to the latest Game Ready / Studio driver (from
   GeForce Experience or nvidia.com). This single Windows driver also powers the GPU
   inside WSL2 — **do NOT install an NVIDIA driver inside WSL.**
3. ~20 GB free disk (model weights + checkpoints).

---

## Step 1 — Install WSL2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL2 + Ubuntu in one go. **Reboot when it asks.** After reboot, an
Ubuntu window opens and asks you to create a **username and password** (this is your
Linux user — the password won't show as you type; that's normal).

Verify the version is 2:

```powershell
wsl --list --verbose      # VERSION column should say 2
```

If Ubuntu didn't open, launch "Ubuntu" from the Start menu. From here on, commands
run **inside the Ubuntu terminal** unless noted.

---

## Step 2 — Confirm the GPU is visible in WSL

Inside Ubuntu:

```bash
nvidia-smi
```

You should see your RTX 4060 and the same driver version as Windows. If this works,
GPU passthrough is good. (If it says "command not found", update your Windows driver
and restart WSL with `wsl --shutdown` in PowerShell, then reopen Ubuntu.)

---

## Step 3 — Install Python 3.11 in Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev git
python3.11 --version       # should print 3.11.x
```

---

## Step 4 — Get the project into WSL

Your repo lives on Windows at `C:\Users\Leo12\Documents\ai-vtuber`, which Ubuntu sees
at `/mnt/c/Users/Leo12/Documents/ai-vtuber`. Training reads/writes lots of small files,
and `/mnt/c` is slow — so **copy the repo into the Linux home** for speed:

```bash
cp -r /mnt/c/Users/Leo12/Documents/ai-vtuber ~/ai-vtuber
cd ~/ai-vtuber
ls data/elysia_train.jsonl     # confirm the dataset came along
```

(When training finishes you'll copy the adapter back to Windows — covered in Step 9.)

> Alternative: if you pushed the repo to GitHub, `git clone` it into `~` instead.

---

## Step 5 — Create the training environment

```bash
cd ~/ai-vtuber
python3.11 -m venv .venv-train
source .venv-train/bin/activate     # you'll do this every new terminal

pip install --upgrade pip

# 1) Install the CUDA build of PyTorch FIRST (from its own index):
pip install torch --index-url https://download.pytorch.org/whl/cu124

# 2) Then the rest of the training stack:
pip install -r requirements-train.txt
```

> If `cu124` ever fails, `cu126` also works on a 4060:
> `pip install torch --index-url https://download.pytorch.org/whl/cu126`

---

## Step 6 — Verify PyTorch sees the GPU

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0))"
```

Expected: `CUDA: True | GPU: NVIDIA GeForce RTX 4060`. If it says `False`, recheck
Step 2 and that you installed the cu124/cu126 torch (not the default CPU wheel).

---

## Step 7 — Smoke test the trainer (≈2–5 min)

This proves the whole pipeline works before you commit to a long run. It trains on
just 8 examples for 1 step-y epoch and downloads the base model on first use.

```bash
python train/sft_lora.py --data data/elysia_train.jsonl --model Qwen/Qwen3-4B --smoke
```

First run downloads Qwen3-4B (~8 GB) to `~/.cache/huggingface` — that's a one-time
wait. Success ends with: `SMOKE OK — pipeline runs end to end.`

If you hit an out-of-memory error even here, see Troubleshooting.

---

## Step 8 — The real training run (a few hours)

```bash
python train/sft_lora.py \
    --data data/elysia_train.jsonl \
    --model Qwen/Qwen3-4B \
    --out output/lora-elysia-v1 \
    --epochs 3
```

What to watch: the `loss` printed every few steps should trend **down**. When it
finishes, your adapter is saved to `output/lora-elysia-v1/` (small — a few hundred MB).

Tips:
- Start with **Qwen3-4B** (faster, comfortable on 8 GB). Move to `Qwen3-8B` later if
  you want a bit more quality and have patience.
- Watch VRAM in a second Ubuntu tab with `watch -n 2 nvidia-smi`. If it's near 8 GB,
  lower `--max-seq-len` (e.g. 768) or keep `--batch 1`.

---

## Step 9 — Did it help? Evaluate vs. your baseline

This is the whole point of having a baseline. Run your existing health-check against
the **same** eval set, loading the adapter on top of the base model:

```bash
python scripts/posttrain/post_train_health_check.py \
    --character elysia \
    --base-model Qwen/Qwen3-4B \
    --adapter output/lora-elysia-v1 \
    --eval-file eval/elysia_eval.jsonl \
    --out posttrain_results/elysia_v1.jsonl \
    --load-4bit
```

Compare the pass rate to your baseline (`elysia_results.summary.json`: 33/40, with the
7 failures all being English→Chinese drift). **Success = those language-drift failures
mostly disappear, without breaking the Chinese 10/10.** If English is still drifting,
add more English examples and re-train (the dataset is the lever).

> Overfitting check: if it now repeats catchphrases or sounds stiff, reduce
> `--epochs` to 2 and re-run.

---

## Step 10 — Serve the tuned Elysia through Ollama

Once you're happy with the eval, turn the adapter into an Ollama model so your app
uses it with a one-line config change.

**10a. Merge the adapter into the base weights** (using your existing script):

```bash
python scripts/posttrain/merge_lora_for_export.py \
    --base-model Qwen/Qwen3-4B \
    --adapter output/lora-elysia-v1 \
    --out output/elysia-merged
```

**10b. Convert to GGUF + quantize** (with llama.cpp):

```bash
# one-time: get llama.cpp's converter
cd ~ && git clone https://github.com/ggerganov/llama.cpp
pip install -r llama.cpp/requirements.txt

# convert the merged HF model to GGUF, then quantize to a small, fast q4_K_M
python llama.cpp/convert_hf_to_gguf.py ~/ai-vtuber/output/elysia-merged \
    --outfile ~/ai-vtuber/output/elysia.gguf --outtype f16
# build llama.cpp once (cmake) if needed, then:
~/llama.cpp/build/bin/llama-quantize ~/ai-vtuber/output/elysia.gguf \
    ~/ai-vtuber/output/elysia-q4_k_m.gguf q4_K_M
```

**10c. Copy the GGUF back to Windows and register it with Ollama** (run in PowerShell):

```powershell
copy \\wsl$\Ubuntu\home\<your-wsl-user>\ai-vtuber\output\elysia-q4_k_m.gguf C:\Users\Leo12\Documents\ai-vtuber\models\
```

Create a file `Modelfile.elysia-ft` in your repo:

```
FROM ./models/elysia-q4_k_m.gguf
PARAMETER temperature 0.92
SYSTEM """You are Elysia, the warm, playful Miss Pink Elf VTuber. Reply in the same language as the viewer. Keep replies short and graceful."""
```

Then:

```powershell
cd C:\Users\Leo12\Documents\ai-vtuber
ollama create elysia-ft -f Modelfile.elysia-ft
```

Finally, point your app at it — in `config.elysia.json` set:

```json
"ollama_model": "elysia-ft"
```

Run `python -m aivtuber.cli` and chat. The personality now lives in the weights, so
you can keep the system prompt short.

---

## Troubleshooting

**`CUDA out of memory`** — lower memory pressure, in this order: `--max-seq-len 768`,
keep `--batch 1`, raise `--grad-accum 32`, or switch to a smaller base (`Qwen3-4B`
instead of 8B). Close other GPU apps (games, browsers with video).

**`bitsandbytes` import / CUDA errors** — make sure you're in WSL2 (not native
Windows), that `nvidia-smi` works in WSL, and that torch was installed from the
cu124/cu126 index. Reinstall: `pip install -U bitsandbytes`.

**`nvidia-smi: command not found` in WSL** — update the Windows driver, then in
PowerShell run `wsl --shutdown` and reopen Ubuntu.

**Training is extremely slow** — you're probably running from `/mnt/c`. Train from
`~/ai-vtuber` (Step 4). Also confirm `CUDA: True` (Step 6) — a CPU-only torch is the
usual culprit.

**Model download is slow / interrupted** — it resumes; just re-run. Files cache in
`~/.cache/huggingface`.

**Chat template / `enable_thinking` error** — the trainer already falls back
automatically; no action needed.

---

## Quick reference (after first-time setup)

```bash
cd ~/ai-vtuber && source .venv-train/bin/activate
python train/sft_lora.py --data data/elysia_train.jsonl --model Qwen/Qwen3-4B --out output/lora-elysia-v2 --epochs 3
python scripts/posttrain/post_train_health_check.py --character elysia --base-model Qwen/Qwen3-4B --adapter output/lora-elysia-v2 --eval-file eval/elysia_eval.jsonl --out posttrain_results/elysia_v2.jsonl --load-4bit
```

Iterate: improve `data/elysia_train.jsonl` → retrain → re-eval → compare. The data is
where the gains are.
