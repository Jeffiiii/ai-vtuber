"""Text-to-speech (Stage 2). Not implemented yet — interface stub only.

Plan: a `TTSBackend` ABC with `speak(text) -> audio` / `stream_speak(text)`, with
backends for Coqui XTTSv2 (local, free, supports Chinese & English) and a cloud
option (ElevenLabs / Azure). Route output through a virtual audio cable so the
Live2D avatar can lip-sync in Stage 3.
"""
