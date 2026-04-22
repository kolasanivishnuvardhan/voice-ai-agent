"""WebSocket pipeline orchestrator for real-time multilingual voice interactions."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import WebSocket

from agent.prompt.system_prompt import build_system_prompt
from agent.reasoning.llm_agent import LLMAgent
from memory.persistent_memory import PersistentMemory
from memory.session_memory import SessionMemory
from services.language_detection.lang_service import normalize_language
from services.speech_to_text.stt_service import STTService
from services.text_to_speech.tts_service import TTSService

logger = structlog.get_logger(__name__)

SPECIALIZATION_ALIASES: dict[str, str] = {
    "cardio": "cardiology",
    "cardiologist": "cardiology",
    "cardiology": "cardiology",
    "derma": "dermatology",
    "dermatologist": "dermatology",
    "dermatology": "dermatology",
    "neuro": "neurology",
    "neurologist": "neurology",
    "neurology": "neurology",
    "pedia": "pediatrics",
    "pediatric": "pediatrics",
    "pediatrics": "pediatrics",
    "general physician": "general",
    "general": "general",
}


def _extract_specialization(text: str) -> str | None:
    """Extract normalized doctor specialization from free text."""
    raw = (text or "").lower()
    for key, normalized in SPECIALIZATION_ALIASES.items():
        if key in raw:
            return normalized
    return None


def _extract_date_value(text: str) -> str | None:
    """Extract a date token that appointment engine can parse."""
    raw = (text or "").lower().strip()

    if "today" in raw or "to day" in raw or "current date" in raw:
        return "today"
    if "tomorrow" in raw or "next day" in raw:
        return "tomorrow"

    iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", raw)
    if iso_match:
        return iso_match.group(0)

    dmy_match = re.search(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b", raw)
    if dmy_match:
        return dmy_match.group(0)

    return None


def _extract_time_slot(text: str) -> str | None:
    """Extract a likely HH:MM slot from user utterance."""
    raw = (text or "").lower().strip()
    match_hhmm = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\s*(am|pm)?\b", raw)
    if match_hhmm:
        hour = int(match_hhmm.group(1))
        minute = int(match_hhmm.group(2))
        meridian = match_hhmm.group(3)
        if meridian == "pm" and hour < 12:
            hour += 12
        if meridian == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    match_hour = re.search(r"\b([1-9]|1[0-2])\s*(a\.?m\.?|p\.?m\.?|a|p)\b", raw)
    if match_hour:
        hour = int(match_hour.group(1))
        meridian = match_hour.group(2).replace(".", "")
        if meridian.startswith("p") and hour < 12:
            hour += 12
        if meridian.startswith("a") and hour == 12:
            hour = 0
        return f"{hour:02d}:00"

    return None


def _extract_contextual_slot_choice(text: str, available_slots: list[str]) -> str | None:
    """Extract time from short follow-ups like '9' or '9 o clock' using available slots context."""
    if not available_slots:
        return None

    raw = (text or "").lower().strip()
    normalized = re.sub(r"\s+", " ", raw)

    direct_time = _extract_time_slot(normalized)
    if direct_time:
        selected = _select_slot(available_slots, direct_time)
        if selected:
            return selected

    match_oclock = re.search(r"\b([1-9]|1[0-2]|2[0-3])\s*o'?\s*clock\b", normalized)
    if match_oclock:
        hour = int(match_oclock.group(1))
        return _select_slot(available_slots, f"{hour:02d}:00")

    compact = re.fullmatch(r"(?:at\s+)?([1-9]|1[0-2]|2[0-3])", normalized)
    if compact:
        hour = int(compact.group(1))
        return _select_slot(available_slots, f"{hour:02d}:00")

    return None


def _has_date_or_specialization(text: str) -> bool:
    """Check if user text contains explicit date/specialization details."""
    raw = (text or "").lower()
    if any(k in raw for k in ["today", "tomorrow", "current date"]):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}[-/]\d{2}[-/]\d{4}\b", raw):
        return True
    specialization_terms = [
        "cardio",
        "cardiology",
        "cardiologist",
        "derma",
        "dermatologist",
        "neuro",
        "neurologist",
        "pediatric",
        "general physician",
        "doctor",
    ]
    return any(term in raw for term in specialization_terms)


def _select_slot(available_slots: list[str], requested_time: str | None) -> str | None:
    """Pick the best slot match from available slots based on requested time."""
    if not available_slots:
        return None
    if not requested_time:
        return None

    if requested_time in available_slots:
        return requested_time

    requested_hour = requested_time.split(":")[0]
    for slot in available_slots:
        if slot.startswith(f"{requested_hour}:"):
            return slot

    return None


async def handle_voice_websocket(
    websocket: WebSocket,
    session_id: str,
    stt_service: STTService,
    tts_service: TTSService,
    session_memory: SessionMemory,
    persistent_memory: PersistentMemory,
    llm_agent: LLMAgent,
    latency_stats: list[dict[str, Any]],
) -> None:
    """Run the complete receive->STT->agent->TTS->send pipeline for each audio frame."""
    await websocket.accept()
    session_state: dict[str, Any] = await session_memory.load_session(session_id)

    while True:
        audio_bytes: bytes = await websocket.receive_bytes()
        t_start: float = time.time()

        stt_result: dict[str, Any] = await stt_service.transcribe(audio_bytes)
        text: str = stt_result["text"]
        whisper_lang: str = stt_result["detected_language"]
        t_stt: float = time.time()

        language: str = normalize_language(whisper_lang, text, session_state.get("preferred_language", "en"))
        t_lang: float = time.time()

        if not text.strip():
            t_end: float = time.time()
            pipeline_log: dict[str, Any] = {
                "session_id": session_id,
                "total_ms": round((t_end - t_start) * 1000),
                "stages": {
                    "stt_ms": round((t_stt - t_start) * 1000),
                    "lang_ms": round((t_lang - t_stt) * 1000),
                    "mem_load_ms": 0,
                    "agent_ms": 0,
                    "mem_save_ms": 0,
                    "tts_ms": 0,
                    "send_ms": 0,
                },
                "language": language,
                "tool_called": None,
                "intent": "empty_input",
                "transcript": {"user": "", "assistant": ""},
            }
            latency_stats.append(pipeline_log)
            if len(latency_stats) > 100:
                latency_stats.pop(0)

            logger.info("pipeline_skipped_empty_transcript", **pipeline_log)
            await websocket.send_json(
                {
                    "type": "metadata",
                    "latency_ms": pipeline_log["total_ms"],
                    "stages": pipeline_log["stages"],
                    "user_text": "",
                    "assistant_text": "I couldn't hear you clearly. Please try again and speak for 1-2 seconds.",
                }
            )
            continue

        session_state = await session_memory.load_session(session_id)
        patient_mem: dict[str, Any] = await persistent_memory.load_patient_memory(session_state["patient_id"])
        t_mem: float = time.time()

        session_state.setdefault("pending_details", {"specialization": None, "date": None, "time": None, "doctor_id": None, "available_slots": []})
        session_state.setdefault("pending_intent", None)
        pending_details: dict[str, Any] = session_state.get("pending_details", {})
        pending_details.setdefault("available_slots", [])

        extracted_specialization = _extract_specialization(text)
        extracted_date = _extract_date_value(text)
        time_choice: str | None = _extract_time_slot(text)

        if not time_choice:
            contextual_slot = _extract_contextual_slot_choice(text, pending_details.get("available_slots", []))
            if contextual_slot:
                time_choice = contextual_slot

        if extracted_specialization:
            pending_details["specialization"] = extracted_specialization
        if extracted_date:
            pending_details["date"] = extracted_date
        if time_choice:
            pending_details["time"] = time_choice

        lower_text = text.lower()
        is_booking_intent = (
            "book" in lower_text
            or "appointment" in lower_text
            or session_state.get("pending_intent") == "book"
            or bool(time_choice and pending_details.get("doctor_id") and pending_details.get("date"))
        )

        deterministic_response: str | None = None
        deterministic_tool_called: str | None = None

        if is_booking_intent:
            session_state["pending_intent"] = "book"

            specialization_for_lookup = pending_details.get("specialization")
            date_for_lookup = pending_details.get("date")

            if specialization_for_lookup and date_for_lookup:
                need_refresh_availability = (
                    not pending_details.get("doctor_id")
                    or not pending_details.get("available_slots")
                    or extracted_specialization is not None
                    or extracted_date is not None
                )

                if need_refresh_availability:
                    deterministic_tool_called = "checkAvailability"
                    availability_result = await llm_agent.tool_executor.execute(
                        "checkAvailability",
                        {
                            "doctor_specialization": specialization_for_lookup,
                            "date": date_for_lookup,
                        },
                    )

                    if isinstance(availability_result, list) and availability_result:
                        first_doctor = availability_result[0]
                        pending_details["doctor_id"] = first_doctor.get("doctor_id")
                        pending_details["available_slots"] = first_doctor.get("available_slots", [])
                    else:
                        deterministic_response = (
                            "I could not find available slots for that specialization/date. "
                            "Please try another date, like tomorrow."
                        )

                if deterministic_response is None:
                    selected_slot = _select_slot(pending_details.get("available_slots", []), pending_details.get("time"))
                    if selected_slot and pending_details.get("doctor_id"):
                        deterministic_tool_called = "bookAppointment"
                        booking_result = await llm_agent.tool_executor.execute(
                            "bookAppointment",
                            {
                                "patient_id": session_state["patient_id"],
                                "doctor_id": pending_details["doctor_id"],
                                "date": date_for_lookup,
                                "time": selected_slot,
                            },
                        )

                        if isinstance(booking_result, dict) and booking_result.get("appointment_id"):
                            deterministic_response = (
                                f"Booked successfully for {date_for_lookup} at {selected_slot}. "
                                f"Your appointment ID is {booking_result['appointment_id']}."
                            )
                            session_state["pending_intent"] = None
                            session_state["pending_details"] = {
                                "specialization": None,
                                "date": None,
                                "time": None,
                                "doctor_id": None,
                                "available_slots": [],
                            }
                            pending_details = session_state["pending_details"]
                        else:
                            message = "Unable to book this slot right now."
                            if isinstance(booking_result, dict) and booking_result.get("message"):
                                message = str(booking_result["message"])
                            deterministic_response = f"{message} Please choose another available time."
                    else:
                        slots = pending_details.get("available_slots", [])
                        if slots:
                            slots_text = ", ".join(slots[:6])
                            deterministic_response = (
                                f"I found available slots on {date_for_lookup}: {slots_text}. "
                                "Please tell me your preferred time."
                            )
                        else:
                            deterministic_response = (
                                "Please share a preferred date like today or tomorrow, "
                                "and I will fetch available slots."
                            )
            else:
                missing_parts = []
                if not specialization_for_lookup:
                    missing_parts.append("specialization")
                if not date_for_lookup:
                    missing_parts.append("date")
                deterministic_response = (
                    "Please share " + " and ".join(missing_parts) + " for the appointment booking."
                )

        if deterministic_response is not None:
            agent_result = {
                "response_text": deterministic_response,
                "tool_called": deterministic_tool_called,
                "tool_executions": [],
                "reasoning_trace": [],
                "intent": "appointment_management",
            }
        else:
            user_text_for_agent: str = text
            can_use_context: bool = (
                session_state.get("pending_intent") == "book"
                and bool(pending_details.get("doctor_id"))
                and bool(pending_details.get("date"))
                and bool(time_choice)
                and not _has_date_or_specialization(text)
            )
            if can_use_context:
                user_text_for_agent = (
                    "Use booking context from previous turn. "
                    f"patient_id={session_state['patient_id']}, doctor_id={pending_details.get('doctor_id')}, "
                    f"date={pending_details.get('date')}, specialization={pending_details.get('specialization')}. "
                    f"User selected time {time_choice}. Confirm and call bookAppointment."
                )

            system_prompt: str = build_system_prompt(language, session_state, patient_mem)
            agent_result = await llm_agent.run(
                system_prompt=system_prompt,
                conversation_history=session_state.get("conversation_history", []),
                user_text=user_text_for_agent,
            )
            if not str(agent_result.get("response_text", "")).strip():
                agent_result["response_text"] = "Please share a doctor specialization and date to continue booking."

            for execution in agent_result.get("tool_executions", []):
                tool_name = execution.get("name")
                tool_args = execution.get("arguments", {})
                tool_result = execution.get("result")

                if tool_name == "checkAvailability" and isinstance(tool_result, list) and tool_result:
                    first_doctor = tool_result[0]
                    pending_details.update(
                        {
                            "specialization": tool_args.get("doctor_specialization"),
                            "date": tool_args.get("date"),
                            "doctor_id": first_doctor.get("doctor_id"),
                            "available_slots": first_doctor.get("available_slots", []),
                        }
                    )
                    session_state["pending_intent"] = "book"

                if tool_name == "bookAppointment" and isinstance(tool_result, dict) and tool_result.get("appointment_id"):
                    session_state["pending_intent"] = None
                    session_state["pending_details"] = {
                        "specialization": None,
                        "date": None,
                        "time": None,
                        "doctor_id": None,
                        "available_slots": [],
                    }

            if time_choice and session_state.get("pending_intent") == "book":
                session_state["pending_details"]["time"] = time_choice
        t_agent: float = time.time()

        session_state["language"] = language
        session_state["preferred_language"] = language
        session_state.setdefault("conversation_history", []).append({"role": "user", "content": text})
        session_state["conversation_history"].append(
            {"role": "assistant", "content": agent_result["response_text"]}
        )
        await session_memory.save_session(session_id, session_state)
        await persistent_memory.update_patient_memory(
            session_state["patient_id"],
            {
                "preferred_language": language,
                "last_interaction": datetime.now(timezone.utc).isoformat(),
            },
        )
        t_mem_save: float = time.time()

        try:
            tts_result: dict[str, Any] = await tts_service.synthesize(agent_result["response_text"], language)
        except Exception as exc:  # noqa: BLE001
            logger.warning("tts_failed", session_id=session_id, error=str(exc))
            tts_result = {"audio_bytes": b"", "format": "mp3", "duration_ms": 0}
        t_tts: float = time.time()

        audio_bytes_out: bytes = tts_result.get("audio_bytes", b"")
        if audio_bytes_out:
            await websocket.send_bytes(audio_bytes_out)
        t_end: float = time.time()

        pipeline_log: dict[str, Any] = {
            "session_id": session_id,
            "total_ms": round((t_end - t_start) * 1000),
            "stages": {
                "stt_ms": round((t_stt - t_start) * 1000),
                "lang_ms": round((t_lang - t_stt) * 1000),
                "mem_load_ms": round((t_mem - t_lang) * 1000),
                "agent_ms": round((t_agent - t_mem) * 1000),
                "mem_save_ms": round((t_mem_save - t_agent) * 1000),
                "tts_ms": round((t_tts - t_mem_save) * 1000),
                "send_ms": round((t_end - t_tts) * 1000),
            },
            "language": language,
            "tool_called": agent_result.get("tool_called"),
            "intent": agent_result.get("intent"),
            "transcript": {"user": text, "assistant": agent_result["response_text"]},
        }
        latency_stats.append(pipeline_log)
        if len(latency_stats) > 100:
            latency_stats.pop(0)

        logger.info("pipeline_complete", **pipeline_log)

        await websocket.send_json(
            {
                "type": "metadata",
                "latency_ms": pipeline_log["total_ms"],
                "stages": pipeline_log["stages"],
                "user_text": text,
                "assistant_text": agent_result["response_text"],
            }
        )
