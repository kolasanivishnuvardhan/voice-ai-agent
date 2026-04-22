"""Language normalization service using Whisper output and langdetect fallback."""

from __future__ import annotations

import os
from typing import Final

from langdetect import detect

try:
    import fasttext
except Exception:  # noqa: BLE001
    fasttext = None

SUPPORTED: Final[set[str]] = {"hi", "ta", "en"}
WHISPER_MAP: Final[dict[str, str]] = {
    "hindi": "hi",
    "hi": "hi",
    "tamil": "ta",
    "ta": "ta",
    "english": "en",
    "en": "en",
}


def _fasttext_detect(text: str) -> str:
    """Detect language using optional fastText model if configured."""
    model_path: str = os.getenv("FASTTEXT_MODEL_PATH", "")
    if fasttext is None or not model_path or not os.path.exists(model_path) or not text.strip():
        return ""
    model = fasttext.load_model(model_path)
    labels, _ = model.predict(text.replace("\n", " "), k=1)
    if not labels:
        return ""
    label: str = labels[0].replace("__label__", "")
    return WHISPER_MAP.get(label.lower(), label.lower())


def normalize_language(whisper_lang: str, text: str, patient_preferred: str) -> str:
    """Normalize language to one of en/hi/ta."""
    mapped_whisper: str = WHISPER_MAP.get((whisper_lang or "").strip().lower(), "")
    if mapped_whisper in SUPPORTED:
        return mapped_whisper

    try:
        detected: str = detect(text) if text.strip() else ""
        mapped_detected: str = WHISPER_MAP.get(detected.lower(), detected.lower())
        if mapped_detected in SUPPORTED:
            return mapped_detected
    except Exception:
        pass

    fasttext_detected: str = _fasttext_detect(text)
    if fasttext_detected in SUPPORTED:
        return fasttext_detected

    preferred: str = patient_preferred.lower() if patient_preferred else ""
    if preferred in SUPPORTED:
        return preferred

    return "en"
