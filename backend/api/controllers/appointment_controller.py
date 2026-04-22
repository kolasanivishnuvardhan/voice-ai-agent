"""Controller layer for appointment route handlers."""

from __future__ import annotations

from typing import Any

from scheduler.appointment_engine import AppointmentEngine


class AppointmentController:
    """Coordinates appointment operations through AppointmentEngine."""

    def __init__(self, engine: AppointmentEngine) -> None:
        self.engine: AppointmentEngine = engine

    async def check_availability(self, specialization: str, date: str) -> list[dict[str, Any]]:
        """Controller passthrough for availability."""
        return await self.engine.check_availability(specialization, date)

    async def book_appointment(self, payload: dict[str, str]) -> dict[str, Any]:
        """Controller passthrough for booking."""
        return await self.engine.book_appointment(
            patient_id=payload["patient_id"],
            doctor_id=payload["doctor_id"],
            date_str=payload["date"],
            time_slot=payload["time"],
        )

    async def cancel_appointment(self, appointment_id: str) -> dict[str, Any]:
        """Controller passthrough for cancellation."""
        return await self.engine.cancel_appointment(appointment_id)

    async def reschedule_appointment(self, payload: dict[str, str]) -> dict[str, Any]:
        """Controller passthrough for reschedule."""
        return await self.engine.reschedule_appointment(
            appointment_id=payload["appointment_id"],
            new_date=payload["new_date"],
            new_time=payload["new_time"],
        )

    async def get_patient_history(self, patient_id: str) -> list[dict[str, Any]]:
        """Controller passthrough for history retrieval."""
        return await self.engine.get_patient_history(patient_id)
