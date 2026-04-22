# Architecture

```text
Browser Mic -> WebSocket (/ws/voice/{session_id})
            -> STT (Whisper tiny, local)
            -> Language Normalize (whisper + langdetect)
            -> Redis Session + Patient Memory Load
            -> Groq Llama 3.3 70B Agent (tool-calling loop)
            -> Appointment Tools (PostgreSQL via SQLAlchemy)
            -> Redis Memory Save
            -> TTS (gTTS, pyttsx3 fallback)
            -> Audio bytes back to browser
```

Each request records stage-level latency and emits structured JSON logs via structlog.
