"""VTube Studio avatar controller via its plugin API (websocket).

Install: pip install websocket-client
In VTube Studio: Settings -> enable "Start API (allow plugins)". Default port 8001.
Create expression hotkeys in VTS (one per emotion), then map them in config under
`avatar_expressions` (emotion -> hotkey NAME exactly as shown in VTS).

First run pops an "allow plugin" prompt in VTS; approve it. The auth token is saved
to .vts_token so later runs connect silently.
"""

from __future__ import annotations

import json
import os
import uuid

from .base import AvatarController

_TOKEN_FILE = ".vts_token"


def _envelope(message_type: str, data: dict | None = None) -> str:
    return json.dumps({
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": uuid.uuid4().hex[:8],
        "messageType": message_type,
        "data": data or {},
    })


class VTubeStudioAvatar(AvatarController):
    def __init__(self, url: str = "ws://localhost:8001",
                 expressions: dict | None = None,
                 plugin_name: str = "ai-vtuber (Elysia)",
                 developer: str = "Jeffi",
                 token_path: str = _TOKEN_FILE):
        self.url = url
        self.expressions = expressions or {}   # emotion -> hotkey name
        self.plugin_name = plugin_name
        self.developer = developer
        self.token_path = token_path
        self._ws = None
        self._hotkeys: dict[str, str] = {}     # hotkey name -> hotkey id

    # ------------------------------------------------------------------
    def _send(self, message_type: str, data: dict | None = None) -> dict:
        self._ws.send(_envelope(message_type, data))
        return json.loads(self._ws.recv())

    def _load_token(self) -> str | None:
        try:
            with open(self.token_path) as f:
                return f.read().strip() or None
        except FileNotFoundError:
            return None

    def _save_token(self, token: str) -> None:
        try:
            with open(self.token_path, "w") as f:
                f.write(token)
        except OSError:
            pass

    def connect(self) -> tuple[bool, str]:
        try:
            import websocket  # websocket-client
        except ImportError:
            return False, "websocket-client not installed. Run: pip install websocket-client"
        try:
            self._ws = websocket.create_connection(self.url, timeout=10)
        except Exception as e:
            return False, f"Can't reach VTube Studio at {self.url}. Enable its API. ({e})"

        info = {"pluginName": self.plugin_name, "pluginDeveloper": self.developer}

        token = self._load_token()
        if not token:
            resp = self._send("AuthenticationTokenRequest", info)
            token = (resp.get("data") or {}).get("authenticationToken")
            if not token:
                return False, "VTS did not grant a token (approve the plugin prompt, then retry)."
            self._save_token(token)

        auth = self._send("AuthenticationRequest", {**info, "authenticationToken": token})
        if not (auth.get("data") or {}).get("authenticated"):
            # token may be stale; clear it so next run re-requests
            try:
                os.remove(self.token_path)
            except OSError:
                pass
            return False, "VTS auth failed (token cleared — rerun and approve the prompt)."

        self._refresh_hotkeys()
        return True, f"VTube Studio connected ({len(self._hotkeys)} hotkeys)"

    def _refresh_hotkeys(self):
        try:
            resp = self._send("HotkeysInCurrentModelRequest", {})
            hk = (resp.get("data") or {}).get("availableHotkeys", [])
            self._hotkeys = {h.get("name", ""): h.get("hotkeyID", "") for h in hk}
        except Exception:
            self._hotkeys = {}

    # ------------------------------------------------------------------
    def set_emotion(self, emotion: str) -> None:
        if not self._ws:
            return
        hotkey_name = self.expressions.get(emotion)
        if not hotkey_name:
            return
        hotkey_id = self._hotkeys.get(hotkey_name)
        if not hotkey_id:
            return  # name not found in current model; skip silently
        try:
            self._send("HotkeyTriggerRequest", {"hotkeyID": hotkey_id})
        except Exception:
            pass  # best-effort; never break the stream over an expression

    def close(self) -> None:
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return "vtube-studio"
