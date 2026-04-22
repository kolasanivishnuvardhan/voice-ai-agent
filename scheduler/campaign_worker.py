"""Celery worker for outbound reminder and follow-up campaign generation."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Any

from celery import Celery
from celery.schedules import crontab
from groq import Groq
import redis
from sqlalchemy import and_, select

from models.appointment import Appointment
from models.database import SessionLocal
from models.doctor import Doctor
from models.patient import Patient

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BROKER_URL: str = REDIS_URL
RESULT_BACKEND: str = REDIS_URL

celery_app: Celery = Celery("campaign_worker", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.beat_schedule = {
    "daily-reminder-9am-ist": {
        "task": "scheduler.campaign_worker.trigger_tomorrow_reminders",
        "schedule": crontab(hour=9, minute=0),
    }
}


def _get_redis_sync() -> redis.Redis:
    """Create a synchronous Redis client for Celery tasks."""
    return redis.from_url(REDIS_URL, decode_responses=True)


async def _build_campaign_message(
    patient_name: str,
    language: str,
    campaign_type: str,
    doctor_name: str,
    appt_date: str,
    appt_time: str,
) -> str:
    """Generate campaign message using Groq LLM."""
    api_key: str | None = os.getenv("GROQ_API_KEY")
    model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return (
            f"Reminder for {patient_name}: Dr {doctor_name} appointment on {appt_date} at {appt_time}."
        )

    client = Groq(api_key=api_key)
    prompt = (
        f"Generate a {campaign_type} reminder for {patient_name} in {language}. "
        f"Appointment: Dr {doctor_name} on {appt_date} at {appt_time}. Keep it under 3 sentences."
    )
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=120,
    )
    return response.choices[0].message.content or ""


async def _run_campaign_async(patient_id: str, campaign_type: str) -> dict[str, Any]:
    """Execute campaign logic for one patient."""
    redis_client = _get_redis_sync()

    async with SessionLocal() as session:
        patient_stmt = select(Patient).where(Patient.id == patient_id)
        patient_result = await session.execute(patient_stmt)
        patient: Patient | None = patient_result.scalar_one_or_none()
        if patient is None:
            return {"status": "skipped", "reason": "patient_not_found", "patient_id": patient_id}

        appt_stmt = (
            select(Appointment, Doctor)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .where(
                and_(
                    Appointment.patient_id == patient.id,
                    Appointment.status == "confirmed",
                    Appointment.date >= date.today(),
                )
            )
            .order_by(Appointment.date.asc())
            .limit(1)
        )
        appt_result = await session.execute(appt_stmt)
        row = appt_result.first()
        if row is None:
            return {"status": "skipped", "reason": "no_upcoming_appointment", "patient_id": patient_id}

        appointment, doctor = row
        memory_key = f"patient:{patient_id}:memory"
        lang = redis_client.hget(memory_key, "preferred_language") or patient.preferred_language or "en"

        message = await _build_campaign_message(
            patient_name=patient.name,
            language=lang,
            campaign_type=campaign_type,
            doctor_name=doctor.name,
            appt_date=appointment.date.isoformat(),
            appt_time=appointment.time,
        )

        campaign_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "patient_id": str(patient.id),
            "campaign_type": campaign_type,
            "message_sent": message,
            "language": lang,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
        }
        redis_client.set(
            f"campaign:{campaign_id}:{patient.id}",
            json.dumps(payload),
            ex=7 * 24 * 60 * 60,
        )

        return payload


@celery_app.task(name="scheduler.campaign_worker.run_campaign")
def run_campaign(patient_id: str, campaign_type: str) -> dict[str, Any]:
    """Celery task wrapper to execute campaign async code."""
    return asyncio.run(_run_campaign_async(patient_id, campaign_type))


@celery_app.task(name="scheduler.campaign_worker.trigger_tomorrow_reminders")
def trigger_tomorrow_reminders() -> dict[str, Any]:
    """Daily beat task to enqueue reminders for tomorrow's appointments."""

    async def _fetch_patient_ids() -> list[str]:
        async with SessionLocal() as session:
            stmt = select(Appointment.patient_id).where(
                and_(Appointment.date == (date.today() + timedelta(days=1)), Appointment.status == "confirmed")
            )
            result = await session.execute(stmt)
            return [str(pid) for pid in result.scalars().all()]

    patient_ids: list[str] = asyncio.run(_fetch_patient_ids())
    for pid in patient_ids:
        run_campaign.delay(pid, "reminder")
    return {"enqueued": len(patient_ids)}
