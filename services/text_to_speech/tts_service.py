"""Text-to-speech service using gTTS with offline pyttsx3 fallback."""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from gtts import gTTS
import pyttsx3


class TTSService:
    """Multilingual TTS service that prefers gTTS and falls back to pyttsx3."""

    def __init__(self) -> None:
        self.locale_map: dict[str, str] = {
            "en": os.getenv("TTS_LANG_EN", "en-IN"),
            "hi": os.getenv("TTS_LANG_HI", "hi-IN"),
            "ta": os.getenv("TTS_LANG_TA", "ta-IN"),
        }

    def _gtts_synthesize(self, text: str, language: str) -> dict[str, Any]:
        """Synthesize speech via gTTS."""
        if not text.strip():
            return {"audio_bytes": b"", "format": "mp3", "duration_ms": 0, "engine": "none"}
        locale: str = self.locale_map.get(language, self.locale_map["en"])
        t0: float = time.time()
        tts = gTTS(text=text, lang=locale.split("-")[0], slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        duration_ms: int = round((time.time() - t0) * 1000)
        return {"audio_bytes": buf.getvalue(), "format": "mp3", "duration_ms": duration_ms, "engine": "gtts"}

    def _pyttsx3_fallback(self, text: str) -> dict[str, Any]:
        """Fallback synthesis via offline pyttsx3."""
        if not text.strip():
            return {"audio_bytes": b"", "format": "wav", "duration_ms": 0, "engine": "none"}
        t0: float = time.time()
        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            engine.save_to_file(text, str(tmp_path))
            engine.runAndWait()
            data: bytes = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)
        duration_ms: int = round((time.time() - t0) * 1000)
        return {
            "audio_bytes": data,
            "format": "wav",
            "duration_ms": duration_ms,
            "engine": "pyttsx3",
        }

    async def synthesize(self, text: str, language: str) -> dict[str, Any]:
        """Synthesize text to speech using gTTS with fallback."""
        try:
            return await asyncio.to_thread(self._gtts_synthesize, text, language)
        except Exception:
            try:
                return await asyncio.to_thread(self._pyttsx3_fallback, text)
            except Exception:
                return {"audio_bytes": b"", "format": "wav", "duration_ms": 0, "engine": "none"}
