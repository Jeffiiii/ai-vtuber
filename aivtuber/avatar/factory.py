"""Avatar controller factory."""

from __future__ import annotations

from .base import AvatarController, NullAvatar


def create_avatar(config: dict) -> AvatarController:
    name = (config.get("avatar_backend") or "null").lower()

    if name in ("null", "none", "off"):
        return NullAvatar()

    if name in ("vtube-studio", "vtubestudio", "vts"):
        from .vtube_studio import VTubeStudioAvatar
        return VTubeStudioAvatar(
            url=config.get("vts_url", "ws://localhost:8001"),
            expressions=config.get("avatar_expressions", {}),
        )

    raise ValueError(f"Unknown avatar_backend: {name!r}. Use 'null' or 'vtube-studio'.")
