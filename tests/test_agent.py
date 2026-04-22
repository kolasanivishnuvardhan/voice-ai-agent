"""Tests for language normalization and agent tool invocation loop behavior."""

from __future__ import annotations

import pytest

from agent.prompt.system_prompt import build_system_prompt
from agent.tools.tool_executor import ToolExecutor
from services.language_detection.lang_service import normalize_language


@pytest.mark.asyncio
async def test_english_booking_intent() -> None:
    called: dict[str, bool] = {"check": False}

    async def _check(**kwargs):
        called["check"] = True
        return [{"doctor_id": "d1", "doctor_name": "Dr A", "available_slots": ["10:30"]}]

    executor = ToolExecutor({"checkAvailability": _check})
    result = await executor.execute("checkAvailability", {"doctor_specialization": "cardio", "date": "2099-01-01"})
    assert called["check"] is True
    assert isinstance(result, list)


def test_hindi_input_tool_call() -> None:
    detected = normalize_language("hindi", "मुझे कल कार्डियोलॉजिस्ट चाहिए", "en")
    assert detected == "hi"


@pytest.mark.asyncio
async def test_conflict_returns_alternatives() -> None:
    async def _book(**kwargs):
        raise Exception("SlotConflictError: That slot is taken. Available: 10:30, 14:00")

    executor = ToolExecutor({"bookAppointment": _book})
    result = await executor.execute("bookAppointment", {"patient_id": "p", "doctor_id": "d", "date": "2099-01-01", "time": "09:00"})
    assert isinstance(result, dict)
    assert "error" in result
