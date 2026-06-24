# ============================================================================
#  start_stream.ps1 — launch the whole Elysia stack for a Bilibili stream.
#  Opens the LLM brain (WSL), GSVI voice (Windows), and the orchestrator wired
#  to Bilibili + VTube Studio. Edit the paths/IDs below, then run in PowerShell:
#      powershell -ExecutionPolicy Bypass -File .\start_stream.ps1
# ============================================================================

# ---- EDIT THESE ----
$Repo      = "C:\Users\Leo12\Documents\ai-vtuber"
$ModelWsl  = "/mnt/c/Users/Leo12/Documents/ai-vtuber/output/elysia-merged-v2"   # WSL path to the merged model (v2 / v2_1)
$VenvTrain = "~/ai-vtuber/.venv-train/bin/activate"                              # WSL training venv
$GsviDir   = "C:\Users\Leo12\Documents\GPT-SoVITS-1007-cu124\GPT-SoVITS-1007-cu124"  # <-- update if you moved it
$RoomId    = "0"        # <-- your Bilibili live room id (also set bilibili_room_id in config.json)
# --------------------

Write-Host "=== Elysia stream launcher ===" -ForegroundColor Magenta

# 1) LLM brain in WSL (new window)
Write-Host "[1/3] Starting LLM brain (WSL :8000)..." -ForegroundColor Cyan
Start-Process wsl -ArgumentList "bash","-lic","source $VenvTrain && export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 && python $($ModelWsl -replace 'elysia-merged.*','')../serve_elysia.py --model $ModelWsl; exec bash"
# (if the line above is fiddly, just start serve_elysia.py manually — see STREAM_BILIBILI.md)

# 2) GSVI voice (new window)
Write-Host "[2/3] Starting GSVI voice (:8002)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit","-Command","cd `"$GsviDir`"; runtime\python.exe gsvi.py -p 8002"

Write-Host "Waiting 60s for the brain + voice to load..." -ForegroundColor DarkGray
Start-Sleep -Seconds 60

# 3) Orchestrator (this window) — Bilibili danmaku + VTube Studio avatar + voice
Write-Host "[3/3] Going live: Bilibili + VTube Studio..." -ForegroundColor Green
Set-Location $Repo
& ".\.venv\Scripts\Activate.ps1"
python -m aivtuber.orchestrator --platform bilibili --avatar vtube-studio

# When the orchestrator exits, leave the other windows running (close them manually).
