"""Edge-TTS backend — free, online, bilingual (EN/ZH), no GPU, great quality.

The easiest way to give Elysia a voice. Install: pip install edge-tts
Picks a voice by the reply's language and can pitch-up for a cuter tone.
"""

from __future__ import annotations

import asyncio
import shutil

from .base import TTSBackend, detect_lang


class EdgeTTSBackend(TTSBackend):
    def __init__(self, voice_en: str = "en-US-JennyNeural",
                 voice_zh: str = "zh-CN-XiaoxiaoNeural",
                 rate: str = "+0%", pitch: str = "+8Hz"):
        self.voice_en = voice_en
        self.voice_zh = voice_zh
        self.rate = rate
        self.pitch = pitch

    def _voice_for(self, text: str, lang: str | None = None) -> str:
        lang = lang or detect_lang(text)
        return self.voice_zh if lang == "zh" else self.voice_en

    def synthesize(self, text: str, out_path: str, lang: str | None = None) -> str:
        import edge_tts  # lazy: only needed when actually speaking

        if not out_path.endswith(".mp3"):
            out_path = out_path.rsplit(".", 1)[0] + ".mp3"
        voice = self._voice_for(text, lang)

        async def _run():
            com = edge_tts.Communicate(text, voice, rate=self.rate, pitch=self.pitch)
            await com.save(out_path)

        asyncio.run(_run())
        return out_path

    def is_available(self) -> tuple[bool, str]:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return False, "edge-tts not installed. Run: pip install edge-tts"
        # edge-tts needs network access (Microsoft's online voices).
        return True, f"edge-tts ready (en={self.voice_en}, zh={self.voice_zh})"

    @property
    def name(self) -> str:
        return "edge-tts"

    @property
    def output_ext(self) -> str:
        return ".mp3"

    @staticmethod
    def list_voices_hint() -> str:
        return ("Browse voices with: `edge-tts --list-voices`. Nice picks — EN: "
                "en-US-JennyNeural, en-US-AnaNeural, en-GB-SoniaNeural; "
                "ZH: zh-CN-XiaoxiaoNeural, zh-CN-XiaoyiNeural.")
