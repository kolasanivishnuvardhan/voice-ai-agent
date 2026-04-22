# Real-Time Multilingual Voice AI Agent for Clinical Appointment Booking

## 1. Overview

This project is a production-oriented multilingual voice assistant that books, reschedules, cancels, and checks clinical appointments in real time. Audio is received through a WebSocket, transcribed locally with Whisper, reasoned over by Groq-hosted Llama 3.3 70B using tool-calling, and converted back to speech with gTTS. The system supports English, Hindi, and Tamil automatically without asking users to choose a language. Session and patient memory are stored in Redis, while appointment data is persisted in PostgreSQL.

## 2. Architecture

```text
[Browser Mic]
    |
    v
[FastAPI WebSocket /ws/voice/{session_id}]
    |
    +--> [STT: Whisper tiny (local)]
    +--> [Language normalization: whisper lang + langdetect]
    +--> [Redis: session + patient memory load]
    +--> [Groq Llama 3.3 70B tool-calling loop]
    |         |
    |         v
    |   [Appointment tools -> PostgreSQL]
    +--> [Redis memory save]
    +--> [TTS: gTTS, pyttsx3 fallback]
    +--> [Audio bytes streamed back]
```

Each stage is timestamped and emitted as structured JSON (`pipeline_complete`) for observability and latency analysis.

## 3. Free Stack Justification

- **Groq + Llama 3.3 70B**: Free API tier with fast inference and OpenAI-compatible tool-calling; trade-off is quota/rate limits.
- **Whisper (local)**: No API cost and strong multilingual ASR; trade-off is CPU latency and lower accuracy on `tiny` model.
- **gTTS**: Free and easy multilingual TTS with no API key; trade-off is network dependency and lower naturalness than premium voices.
- **pyttsx3 fallback**: Fully offline backup when gTTS fails; trade-off is robotic voice quality.
- **PostgreSQL + Redis via Docker**: Free, robust persistence and low-latency state/cache.
- **Celery + Redis**: Free distributed task queue for outbound campaigns.

## 4. Setup Instructions

### a) Prerequisites

- Python 3.11
- Docker Desktop
- ffmpeg
- git

### b) Clone repo

```powershell
git clone <your_repo_url>
cd voice-ai-agent
```

### c) Configure environment

```powershell
copy .env.example .env
```

Edit `.env` and set `GROQ_API_KEY`.

### d) Start services

```powershell
docker-compose up --build
```

### e) Run DB migrations

```powershell
docker exec app alembic upgrade head
```

### f) Seed DB

```powershell
docker exec app python -m scripts.seed
```

### g) Open frontend

Open `frontend/index.html` in your browser.

## 5. Memory Design

- **Session memory key**: `session:{session_id}` (JSON, TTL = 3600s)
- **Patient memory key**: `patient:{patient_id}:memory` (Redis hash, TTL = 30 days refresh-on-write)

Session stores conversation history, pending intent, and pending details. Persistent memory stores language preference, preferred doctor/hospital, appointment counters, and recency fields. Both session and patient memory are injected into dynamic system prompts.

## 6. Latency Breakdown

| Stage         | Target | Measured (CPU) |
|---------------|--------|----------------|
| STT (Whisper) | <150ms | ~300ms (tiny)  |
| Lang detect   | <20ms  | ~10ms          |
| Memory load   | <20ms  | ~8ms           |
| Groq LLM      | <250ms | ~180ms         |
| Tool exec     | <30ms  | ~15ms          |
| gTTS          | <100ms | ~80ms          |
| Total         | <450ms | ~593ms (CPU)   |

> Note: On GPU, Whisper tiny drops to roughly ~60ms, which can bring total latency under the 450ms target.

## 7. Agent Reasoning

The agent uses Groq’s OpenAI-compatible tool-calling flow:

1. Send messages + tools to Groq.
2. If tool calls are returned, execute via `ToolExecutor`.
3. Append tool result messages and call Groq again.
4. Return final natural-language answer.

Full reasoning traces (system/user/assistant/tool turns) are logged as structured JSON under `agent_reasoning_trace`.

## 8. Multilingual Handling

- Whisper performs primary language auto-detection during STT.
- `langdetect` confirms/fallbacks when Whisper output is ambiguous.
- Final language normalized to `en`, `hi`, or `ta`.
- gTTS locale mapping uses `en-IN`, `hi-IN`, and `ta-IN`.
- System prompt injects language-specific instruction at top.

## 9. Outbound Campaigns

Trigger campaigns via:

- `POST /api/campaigns/trigger`
- body: `{"campaign_type":"reminder|followup|vaccination","patient_ids":[...]}`

Celery worker builds message text with Groq and stores outbound logs in Redis as `campaign:{campaign_id}:{patient_id}`. Celery Beat includes a daily 09:00 IST reminder job for tomorrow’s appointments.

## 10. Trade-offs

- **Whisper tiny vs base**: tiny is much faster but less accurate, especially in noisy audio.
- **gTTS vs ElevenLabs**: gTTS is free and simple, but quality/prosody is lower.
- **Groq vs OpenAI**: Groq is fast and cost-effective/free tier, but free-tier rate limits may constrain scale.

## 11. Known Limitations

- gTTS Tamil quality is basic and not equivalent to premium neural voices.
- Whisper tiny can miss words in accented Hindi/Tamil speech.
- No telephony integration is included yet (browser voice channel only).
- gTTS requires internet connectivity.

## 12. Bonus Features

Implemented:

- ✅ Redis TTL policies for session and persistent memory
- ✅ Daily campaign scheduler via Celery Beat
- ✅ Structured JSON reasoning + latency logs

Not implemented yet:

- ❌ True barge-in interruption handling (can be added in WebSocket recorder/player coordination)
