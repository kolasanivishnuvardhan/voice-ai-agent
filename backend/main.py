"""FastAPI entrypoint with lifespan hooks and WebSocket voice endpoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from celery.schedules import crontab
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import redis.asyncio as redis
import structlog

from agent.reasoning.llm_agent import LLMAgent
from agent.tools.tool_executor import ToolExecutor
from backend.api.routes import appointments, campaigns, health
from backend.websocket.handler import handle_voice_websocket
from memory.persistent_memory import PersistentMemory
from memory.session_memory import SessionMemory
from models.database import SessionLocal
from scheduler.appointment_engine import AppointmentEngine
from scheduler.campaign_worker import celery_app
from services.speech_to_text.stt_service import STTService
from services.text_to_speech.tts_service import TTSService

load_dotenv()
logger = structlog.get_logger(__name__)


def _configure_structlog() -> None:
    """Configure JSON logging for structured latency and trace events."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize long-lived dependencies and release them on shutdown."""
    _configure_structlog()

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)

    stt_service = STTService()
    stt_service.load_model()

    tts_service = TTSService()
    session_memory = SessionMemory(redis_client)
    persistent_memory = PersistentMemory(redis_client)

    app.state.redis = redis_client
    app.state.stt_service = stt_service
    app.state.tts_service = tts_service
    app.state.session_memory = session_memory
    app.state.persistent_memory = persistent_memory
    app.state.latency_stats: list[dict[str, Any]] = []

    celery_app.conf.beat_schedule = {
        "daily-reminder-9am-ist": {
            "task": "scheduler.campaign_worker.trigger_tomorrow_reminders",
            "schedule": crontab(hour=9, minute=0),
        }
    }

    logger.info("startup_complete", whisper_model=stt_service.model_name)
    try:
        yield
    finally:
        await redis_client.close()
        stt_service.unload_model()
        logger.info("shutdown_complete")


app = FastAPI(title="Real-Time Multilingual Voice AI Agent", lifespan=lifespan)
app.include_router(appointments.router)
app.include_router(campaigns.router)
app.include_router(health.router)


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    """Serve frontend home page."""
    index_path = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(index_path)


@app.websocket("/ws/voice/{session_id}")
async def voice_ws(websocket: WebSocket, session_id: str) -> None:
    """Main WebSocket endpoint for bidirectional audio conversations."""
    async with SessionLocal() as db_session:
        engine = AppointmentEngine(db_session, app.state.persistent_memory)
        tool_executor = ToolExecutor(
            {
                "checkAvailability": lambda doctor_specialization, date: engine.check_availability(
                    doctor_specialization, date
                ),
                "bookAppointment": lambda patient_id, doctor_id, date, time: engine.book_appointment(
                    patient_id, doctor_id, date, time
                ),
                "cancelAppointment": lambda appointment_id: engine.cancel_appointment(appointment_id),
                "rescheduleAppointment": lambda appointment_id, new_date, new_time: engine.reschedule_appointment(
                    appointment_id, new_date, new_time
                ),
                "getPatientHistory": lambda patient_id: engine.get_patient_history(patient_id),
            }
        )
        llm_agent = LLMAgent(tool_executor)

        try:
            await handle_voice_websocket(
                websocket=websocket,
                session_id=session_id,
                stt_service=app.state.stt_service,
                tts_service=app.state.tts_service,
                session_memory=app.state.session_memory,
                persistent_memory=app.state.persistent_memory,
                llm_agent=llm_agent,
                latency_stats=app.state.latency_stats,
            )
        except WebSocketDisconnect:
            logger.info("websocket_disconnected", session_id=session_id)
