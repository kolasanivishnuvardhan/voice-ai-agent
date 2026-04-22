"""System prompt builder for multilingual clinical appointment workflows."""

from __future__ import annotations

import json
from typing import Any

from agent.prompt.templates import LANGUAGE_PROMPTS


def build_system_prompt(language: str, session_state: dict[str, Any], patient_memory: dict[str, Any]) -> str:
    """Build robust multilingual prompt with rules and memory context."""
    language_block: str = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])

    rules_block: str = (
        "Rules:\n"
        "- Always call a tool to check availability before confirming any booking\n"
        "- Never hallucinate doctor names, slots, or appointment IDs\n"
        "- If a slot is taken, suggest alternatives from checkAvailability results\n"
        "- Confirm all details (doctor, date, time) before calling bookAppointment\n"
        "- Understand natural dates like 'today', 'tomorrow', and 'current date'\n"
        "- If user gives specialization + date but no time, call checkAvailability and ask user to choose a slot\n"
        "- Accept date formats YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY; convert internally\n"
        "- Keep responses concise — they will be converted to speech"
    )

    session_block: str = (
        "Session context:\n"
        f"pending_intent: {session_state.get('pending_intent')}\n"
        f"pending_details: {json.dumps(session_state.get('pending_details', {}), ensure_ascii=False)}\n"
        f"conversation_stage: {session_state.get('conversation_stage', 'active')}"
    )

    patient_block: str = (
        "Patient memory:\n"
        f"preferred_language: {patient_memory.get('preferred_language', 'en')}\n"
        f"last_doctor: {patient_memory.get('last_appointment_doctor', '')}\n"
        f"last_appointment_date: {patient_memory.get('last_appointment_date', '')}\n"
        f"preferred_hospital: {patient_memory.get('preferred_hospital', '')}"
    )

    return "\n\n".join([language_block, rules_block, session_block, patient_block])
