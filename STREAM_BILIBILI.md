# Going live on Bilibili with Elysia (VTube Studio)

End-to-end: her brain + voice drive a **VTube Studio** Live2D avatar, OBS captures it,
she reads your room's **danmaku** and talks back, and you have a **kill-switch**. This
covers everything up to clicking "开始直播" — the broadcast itself is yours to start.

```
 Bilibili danmaku ─▶ orchestrator ─▶ brain (LLM) ─▶ GSVI voice ─▶ VB-CABLE ─▶ VTS (lip-sync)
                          │                              │                         │
                      moderation                     speakers/monitor          OBS captures VTS ─▶ Bilibili
                       + kill-switch
```

## 0. One-time installs
- **VTube Studio** (Steam) + your Live2D model loaded.
- **VB-CABLE** virtual audio device (vb-audio.com/Cable) — routes Elysia's voice into VTS
  so the mouth lip-syncs to her speech.
- **OBS Studio**.
- The Elysia stack already set up (LLM brain, GSVI voice — see LAUNCH.md).

## 1. Tell her which room (config.json)
```json
{ "bilibili_room_id": 123456 }     // your live room id (the number in live.bilibili.com/<id>)
```
Reading public danmaku needs no login. (Sending messages / some events may need a
`SESSDATA` cookie later — not required to start.)

## 2. Route her voice into VTube Studio (lip-sync)
1. Windows Sound settings → make sure Elysia's audio can reach **VB-CABLE Input**. Easiest:
   set the app/system output to **CABLE Input** while streaming (use a second device or
   "Listen to this device" to also hear her yourself).
2. In **VTube Studio** → Settings → Microphone → choose **CABLE Output**. Turn on
   lip-sync (mouth open by volume). Now her TTS drives the model's mouth.
3. In VTS, enable the **plugin API** (Settings → "Start API", default port `8001`). Create
   **hotkeys** named to match `config.json`'s `avatar_expressions`
   (Happy/Sad/Surprised/Shy/Playful/Neutral) so her emotion switches expressions.

Config already points at VTS:
```json
{ "avatar_backend": "vtube-studio", "vts_url": "ws://localhost:8001" }
```
(The orchestrator flag `--avatar vtube-studio` sets this for the run.)

## 3. OBS scene
- **Source 1 — VTube Studio**: add a *Game Capture* (or *Window Capture*) of VTS; in VTS use
  a transparent/solid background and chroma-key it out in OBS, or use VTS Spout2 → OBS
  Spout2 source for a clean alpha.
- **Source 2 — danmaku (optional)**: a Browser source with a danmaku overlay tool, or a
  capture of the Bilibili 弹幕姬.
- **Source 3 — your audio**: add Elysia's voice as an audio input (monitor VB-CABLE Output),
  so the stream carries her voice. Check OBS Audio Mixer shows her speaking.
- Optionally add the website/desk scene, a "starting soon" image, etc.

## 4. Launch the stack
Easiest — edit the paths at the top of **`start_stream.ps1`** (especially the GSVI folder
you moved and the merged-model path), then:
```powershell
powershell -ExecutionPolicy Bypass -File .\start_stream.ps1
```
Or start the three pieces by hand (see LAUNCH.md): LLM brain (WSL :8000), GSVI (:8002),
then:
```powershell
python -m aivtuber.orchestrator --platform bilibili --avatar vtube-studio
```
Add `--vision` if you want her to react to your screen, `--listen` for mic.

When it prints `LIVE.`, she's reading danmaku and will talk on her own when chat is quiet.

## 5. The kill-switch (type in the orchestrator terminal)
| command | effect |
|---|---|
| `mute` / `m`   | voice off (she keeps "thinking" on screen but is silent) |
| `unmute` / `u` | voice back on |
| `pause` / `p`  | she stops doing anything |
| `resume` / `r` | resume |
| `panic` / `x`  | **mute + pause instantly** — your emergency stop |
| `quit` / `q`   | end the session |

Keep that terminal focused/visible while live. Moderation (input + output) is always on,
but an unscripted model will eventually say something off — `panic` is your safety net.

## 6. Go-live checklist
1. ☐ LLM brain window says `Serving on http://127.0.0.1:8000`.
2. ☐ GSVI window says `Uvicorn running on http://0.0.0.0:8002` (model loaded).
3. ☐ `serve_tts` not needed for the desktop stream (orchestrator calls GSVI directly).
4. ☐ VTS open, model visible, mic = **CABLE Output**, plugin API on (8001), hotkeys created.
5. ☐ Orchestrator: `python -m aivtuber.orchestrator --platform bilibili --avatar vtube-studio`
      → prints `LIVE.` and `Avatar: vtube-studio — connected`.
6. ☐ Say a test line (or wait for an idle muse) → VTS mouth moves, OBS audio meter moves.
7. ☐ OBS preview looks right (avatar keyed, audio present, danmaku overlay).
8. ☐ Kill-switch tested: type `mute` then `unmute`.
9. ☐ Bilibili 直播姬/OBS RTMP key set → **开始直播**.

## 7. First stream tips
- Do a **private/test** broadcast first (low concurrent, or unlisted) to shake out audio
  routing and latency before a public one.
- Watch VRAM: LLM (~6 GB) + GSVI (~2 GB) on the 8 GB card. If OOM, lower the LLM
  `max_tokens` or `gsvi_sample_steps`.
- If her replies feel slow, she still streams sentence-by-sentence; raise
  `director_idle_seconds` so she doesn't talk over herself when chat is busy.
- Have the `panic` command muscle-memorised.
