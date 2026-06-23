"""Avatar control (Stage 3). Backends: null, web (built-in lip-sync), VTube Studio."""

from .base import AvatarController, NullAvatar
from .factory import create_avatar

__all__ = ["AvatarController", "NullAvatar", "create_avatar"]
