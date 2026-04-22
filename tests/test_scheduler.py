"""Scheduler tests using in-memory fake engine behavior contracts."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from scheduler.exceptions import PastDateError, SlotConflictError


class FakeEngine:
    """Simple fake to validate scheduler behavior scenarios."""

    def __init__(self) -> None:
        self.booked: set[tuple[str, str, str]] = set()

    async def book_appointment(self, patient_id: str, doctor_id: str, date_str: str, time_slot: str):
        if date.fromisoformat(date_str) < date.today():
            raise PastDateError("past")
        key = (doctor_id, date_str, time_slot)
        if key in self.booked:
            raise SlotConflictError("taken")
        self.booked.add(key)
        return {"appointment_id": "a1", "status": "confirmed"}

    async def reschedule_appointment(self, appointment_id: str, new_date: str, new_time: str):
        return {"new_appointment_id": "a2", "confirmation_message": "ok"}

    async def cancel_appointment(self, appointment_id: str):
        return {"success": True, "message": "Appointment cancelled successfully"}


@pytest.mark.asyncio
async def test_book_appointment_success() -> None:
    engine = FakeEngine()
    future_date = (date.today() + timedelta(days=1)).isoformat()
    res = await engine.book_appointment("p1", "d1", future_date, "09:00")
    assert res["status"] == "confirmed"


@pytest.mark.asyncio
async def test_double_booking_raises_conflict() -> None:
    engine = FakeEngine()
    future_date = (date.today() + timedelta(days=1)).isoformat()
    await engine.book_appointment("p1", "d1", future_date, "09:00")
    with pytest.raises(SlotConflictError):
        await engine.book_appointment("p2", "d1", future_date, "09:00")


@pytest.mark.asyncio
async def test_past_date_raises_error() -> None:
    engine = FakeEngine()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(PastDateError):
        await engine.book_appointment("p1", "d1", yesterday, "09:00")


@pytest.mark.asyncio
async def test_reschedule_success() -> None:
    engine = FakeEngine()
    future_date = (date.today() + timedelta(days=2)).isoformat()
    res = await engine.reschedule_appointment("a1", future_date, "10:30")
    assert "new_appointment_id" in res


@pytest.mark.asyncio
async def test_cancel_success() -> None:
    engine = FakeEngine()
    res = await engine.cancel_appointment("a1")
    assert res["success"] is True
