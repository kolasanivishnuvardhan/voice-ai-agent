"""Appointment engine with async scheduling, conflict checks, and history retrieval."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.persistent_memory import PersistentMemory
from models.appointment import Appointment
from models.availability import DoctorSchedule
from models.doctor import Doctor
from scheduler.exceptions import DoctorNotFoundError, PastDateError, SlotConflictError, SlotNotAvailableError


class AppointmentEngine:
    """Business logic for appointment scheduling and lifecycle."""

    def __init__(self, db_session: AsyncSession, persistent_memory: PersistentMemory | None = None) -> None:
        self.db_session: AsyncSession = db_session
        self.persistent_memory: PersistentMemory | None = persistent_memory

    @staticmethod
    def _normalize_specialization(specialization: str) -> str:
        """Normalize common specialization synonyms to stored values."""
        raw = (specialization or "").strip().lower()
        synonyms: dict[str, str] = {
            "cardiology": "cardiologist",
            "cardio": "cardiologist",
            "dermatology": "dermatologist",
            "neuro": "neurologist",
            "neurology": "neurologist",
            "pediatrics": "pediatrician",
            "paediatrics": "pediatrician",
            "general medicine": "general physician",
            "gp": "general physician",
        }
        return synonyms.get(raw, raw)

    @staticmethod
    def _resolve_date_input(date_str: str) -> date:
        """Resolve common natural-language date strings to concrete dates."""
        normalized: str = (date_str or "").strip().lower()
        if normalized in {"today", "current date", "current_date", "now"}:
            return date.today()
        if normalized == "tomorrow":
            return date.today() + timedelta(days=1)
        date_raw: str = (date_str or "").strip()
        try:
            return date.fromisoformat(date_raw)
        except ValueError:
            pass

        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_raw, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Unsupported date format: {date_str}")

    async def check_availability(self, specialization: str, date_str: str) -> list[dict[str, Any]]:
        """Return open slots for doctors matching specialization on a date."""
        target_date: date = self._resolve_date_input(date_str)
        normalized_specialization = self._normalize_specialization(specialization)
        doctors_stmt = select(Doctor).where(Doctor.specialization.ilike(f"%{normalized_specialization}%"))
        doctors_result = await self.db_session.execute(doctors_stmt)
        doctors: list[Doctor] = list(doctors_result.scalars().all())

        availability: list[dict[str, Any]] = []
        for doctor in doctors:
            schedule_stmt = select(DoctorSchedule).where(
                and_(DoctorSchedule.doctor_id == doctor.id, DoctorSchedule.date == target_date)
            )
            schedule_result = await self.db_session.execute(schedule_stmt)
            schedule: DoctorSchedule | None = schedule_result.scalar_one_or_none()
            if schedule is None:
                continue

            booked_stmt = select(Appointment.time).where(
                and_(
                    Appointment.doctor_id == doctor.id,
                    Appointment.date == target_date,
                    Appointment.status == "confirmed",
                )
            )
            booked_result = await self.db_session.execute(booked_stmt)
            booked_times: set[str] = {row[0] for row in booked_result.all()}
            all_slots: list[str] = list(schedule.available_slots) if isinstance(schedule.available_slots, list) else []
            open_slots: list[str] = [slot for slot in all_slots if slot not in booked_times]
            availability.append(
                {
                    "doctor_id": str(doctor.id),
                    "doctor_name": doctor.name,
                    "available_slots": open_slots,
                }
            )

        return availability

    async def book_appointment(self, patient_id: str, doctor_id: str, date_str: str, time_slot: str) -> dict[str, Any]:
        """Book a new appointment after schedule and conflict validation."""
        target_date: date = self._resolve_date_input(date_str)
        doctor_uuid = uuid.UUID(doctor_id)
        patient_uuid = uuid.UUID(patient_id)
        if target_date < date.today():
            raise PastDateError("Cannot book appointments in the past")

        doctor_stmt = select(Doctor).where(Doctor.id == doctor_uuid)
        doctor_result = await self.db_session.execute(doctor_stmt)
        doctor: Doctor | None = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise DoctorNotFoundError(f"Doctor not found: {doctor_id}")

        schedule_stmt = select(DoctorSchedule).where(
            and_(DoctorSchedule.doctor_id == doctor.id, DoctorSchedule.date == target_date)
        )
        schedule_result = await self.db_session.execute(schedule_stmt)
        schedule: DoctorSchedule | None = schedule_result.scalar_one_or_none()
        if schedule is None or time_slot not in list(schedule.available_slots):
            raise SlotNotAvailableError("Requested time is not in available schedule")

        existing_stmt = select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor.id,
                Appointment.date == target_date,
                Appointment.time == time_slot,
                Appointment.status == "confirmed",
            )
        )
        existing_result = await self.db_session.execute(existing_stmt)
        existing: Appointment | None = existing_result.scalar_one_or_none()
        if existing is not None:
            alternatives = await self.check_availability(doctor.specialization, date_str)
            alt_slots: list[str] = []
            for item in alternatives:
                if item["doctor_id"] == str(doctor.id):
                    alt_slots = item["available_slots"]
                    break
            raise SlotConflictError(
                f"That slot is taken. Available: {', '.join(alt_slots) if alt_slots else 'none'}"
            )

        appointment = Appointment(
            patient_id=patient_uuid,
            doctor_id=doctor.id,
            date=target_date,
            time=time_slot,
            status="confirmed",
        )
        self.db_session.add(appointment)
        await self.db_session.commit()
        await self.db_session.refresh(appointment)

        if self.persistent_memory is not None:
            existing_memory = await self.persistent_memory.load_patient_memory(patient_id)
            current_count = int(existing_memory.get("appointment_count", "0") or "0")
            await self.persistent_memory.update_patient_memory(
                patient_id,
                {
                    "preferred_doctor_id": str(doctor.id),
                    "last_appointment_date": target_date.isoformat(),
                    "last_appointment_doctor": doctor.name,
                    "preferred_hospital": doctor.hospital,
                    "appointment_count": current_count + 1,
                },
            )

        return {
            "appointment_id": str(appointment.id),
            "doctor_name": doctor.name,
            "date": appointment.date.isoformat(),
            "time": appointment.time,
            "confirmation_message": f"Appointment confirmed with Dr {doctor.name} on {appointment.date} at {appointment.time}",
        }

    async def cancel_appointment(self, appointment_id: str) -> dict[str, Any]:
        """Cancel an existing appointment."""
        appointment_uuid = uuid.UUID(appointment_id)
        stmt = select(Appointment).where(Appointment.id == appointment_uuid)
        result = await self.db_session.execute(stmt)
        appointment: Appointment | None = result.scalar_one_or_none()
        if appointment is None:
            raise ValueError("Appointment not found")

        appointment.status = "cancelled"
        appointment.updated_at = datetime.utcnow()
        await self.db_session.commit()
        return {"success": True, "message": "Appointment cancelled successfully"}

    async def reschedule_appointment(self, appointment_id: str, new_date: str, new_time: str) -> dict[str, Any]:
        """Reschedule appointment by marking old row and inserting a new confirmed row."""
        appointment_uuid = uuid.UUID(appointment_id)
        stmt = select(Appointment).where(Appointment.id == appointment_uuid)
        result = await self.db_session.execute(stmt)
        existing: Appointment | None = result.scalar_one_or_none()
        if existing is None:
            raise ValueError("Appointment not found")

        new_booking = await self.book_appointment(
            patient_id=str(existing.patient_id),
            doctor_id=str(existing.doctor_id),
            date_str=new_date,
            time_slot=new_time,
        )

        existing.status = "rescheduled"
        existing.updated_at = datetime.utcnow()
        await self.db_session.commit()

        return {
            "new_appointment_id": new_booking["appointment_id"],
            "confirmation_message": f"Appointment rescheduled to {new_date} at {new_time}",
        }

    async def get_patient_history(self, patient_id: str) -> list[dict[str, Any]]:
        """Return the latest 10 appointment records joined with doctor details."""
        patient_uuid = uuid.UUID(patient_id)
        stmt = (
            select(Appointment, Doctor)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .where(Appointment.patient_id == patient_uuid)
            .order_by(Appointment.date.desc())
            .limit(10)
        )
        result = await self.db_session.execute(stmt)
        rows = result.all()
        history: list[dict[str, Any]] = []
        for appt, doctor in rows:
            history.append(
                {
                    "date": appt.date.isoformat(),
                    "time": appt.time,
                    "doctor_name": doctor.name,
                    "specialization": doctor.specialization,
                    "status": appt.status,
                }
            )
        return history
