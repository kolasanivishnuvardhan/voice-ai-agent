"""Speech-to-text service using locally hosted Whisper models."""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import whisper


class STTService:
    """Whisper-backed STT service with startup model loading."""

    def __init__(self) -> None:
        self.model_name: str = os.getenv("WHISPER_MODEL", "tiny")
        self.model: Any | None = None

    def load_model(self) -> None:
        """Load Whisper model once during FastAPI lifespan startup."""
        if self.model is None:
            self.model = whisper.load_model(self.model_name)

    def unload_model(self) -> None:
        """Release model reference on shutdown."""
        self.model = None

    def _transcribe_sync(self, audio_bytes: bytes) -> dict[str, Any]:
        """Run Whisper transcription synchronously."""
        if self.model is None:
            raise RuntimeError("Whisper model not loaded. Call load_model() during startup.")

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                temp_path = Path(tmp.name)

            t0: float = time.time()
            result: dict[str, Any] = self.model.transcribe(str(temp_path), language=None)
            duration_ms: int = round((time.time() - t0) * 1000)
            return {
                "text": str(result.get("text", "")).strip(),
                "detected_language": result.get("language", "en"),
                "duration_ms": duration_ms,
            }
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    async def transcribe(self, audio_bytes: bytes) -> dict[str, Any]:
        """Transcribe audio bytes asynchronously using thread offloading."""
        return await asyncio.to_thread(self._transcribe_sync, audio_bytes)
