# Stage 3 — Avatar & Going Live

Scaffolded and ready. As with Stage 2, everything is additive: the console chat
source and the "null" avatar need no extra installs, so you can test the **whole live
loop today**, then turn on Twitch and the VTube Studio avatar piece by piece.

## What's here

```
aivtuber/
├─ emotion.py              # reply text -> emotion label (EN/ZH heuristic)
├─ chat/                   # viewer messages IN
│  ├─ base.py              #   ChatSource ABC + ChatMessage
│  ├─ console_source.py    #   type messages to simulate viewers (no account)
│  ├─ twitch_source.py     #   Twitch chat via twitchio
│  └─ factory.py
├─ avatar/                 # Live2D expressions OUT
│  ├─ base.py              #   AvatarController ABC + NullAvatar (prints emotions)
│  ├─ vtube_studio.py      #   VTube Studio plugin API (websocket)
│  └─ factory.py
└─ live.py                 # the live loop: chat -> Brain -> emotion + voice -> avatar
```

Config keys (in `config.py`): `chat_source`, `twitch_token`, `twitch_channel`,
`avatar_backend`, `vts_url`, `avatar_expressions`.

## Try the loop now (no accounts, no avatar)

```powershell
python -m aivtuber.live
```

Type messages as if you were a viewer; Elysia replies (and speaks, if the Stage 2
voice extras are installed). The avatar is "null" and just prints the chosen emotion.
This proves chat → brain → emotion → voice end to end.

## Turn on the pieces

```powershell
pip install -r requirements-stream.txt    # twitchio + websocket-client

# Twitch chat:
#   1) get an OAuth chat token (e.g. twitchtokengenerator.com), format "oauth:xxxx"
#   2) set twitch_token + twitch_channel in config.json
python -m aivtuber.live --twitch

# VTube Studio avatar:
#   1) open VTube Studio, Settings -> enable "Start API (allow plugins)"
#   2) make expression hotkeys (Happy/Sad/Surprised/Shy/Playful/Neutral) and
#      match their names in config's avatar_expressions
python -m aivtuber.live --avatar          # approve the plugin popup on first run

# everything at once:
python -m aivtuber.live --twitch --avatar
```

## The full live picture (native-app glue you do once)

These are app setups, not pip installs:

1. **Virtual audio cable** (VB-Audio CABLE): route the TTS playback into a virtual
   mic so VTube Studio can lip-sync to Elysia's voice (VTS → mouth tracking → that
   input). The voice loop already produces the audio; this wires it to the mouth.
2. **VTube Studio**: load your Live2D model, set its mouth to follow microphone =
   the virtual cable, and create the expression hotkeys named in your config.
3. **OBS**: add VTube Studio as a window/game capture, add a chat overlay, set up
   your scene, and stream to Twitch/YouTube.

## What's deliberately simple (and the next refinements)

The current `live.py` answers the most recent chat message every couple seconds.
Real Neuro-like behavior adds:
- **Smarter message selection** (pick interesting messages, avoid spam, rate-limit).
- **Autonomy**: talk unprompted when chat is quiet; pick topics; react to events
  (follows/subs/donations) by routing those into the loop.
- **Streaming voice + barge-in**: start speaking the first sentence while the LLM is
  still generating; let the avatar be interrupted. (This is where adopting
  Open-LLM-VTuber's voice layer is worth it — see earlier notes.)
- **Moderation**: filter viewer input and Elysia's output before it's spoken on a
  public stream. Add this before you go public.

## Safety reminder

Once you're live to a public audience, put a moderation/filter pass on both incoming
chat and Elysia's replies, plus a kill switch. An unscripted model will eventually say
something you don't want broadcast — guard it first.
