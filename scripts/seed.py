"""Database seed script for doctors, schedules, and sample patients."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from sqlalchemy import delete, select

from models.availability import DoctorSchedule
from models.database import SessionLocal
from models.doctor import Doctor
from models.patient import Patient

SLOTS: list[str] = ["09:00", "10:30", "12:00", "14:00", "15:30", "17:00"]


async def seed() -> None:
    """Populate initial doctors, schedules, and sample patients."""
    async with SessionLocal() as session:
        await session.execute(delete(DoctorSchedule))
        await session.execute(delete(Doctor))

        doctor_data: list[dict[str, str]] = [
            {"name": "Arun Mehta", "specialization": "cardiologist", "hospital": "City Care Hospital"},
            {"name": "Divya Rao", "specialization": "dermatologist", "hospital": "Skin Health Center"},
            {"name": "Sanjay Iyer", "specialization": "neurologist", "hospital": "NeuroPlus Hospital"},
            {
                "name": "Kavita Sharma",
                "specialization": "general physician",
                "hospital": "Sunrise Clinic",
            },
            {"name": "Raghavan K", "specialization": "pediatrician", "hospital": "Kids First Hospital"},
        ]

        doctors: list[Doctor] = [Doctor(**item) for item in doctor_data]
        session.add_all(doctors)
        await session.flush()

        for doctor in doctors:
            for day_offset in range(7):
                target_date = date.today() + timedelta(days=day_offset)
                session.add(
                    DoctorSchedule(
                        doctor_id=doctor.id,
                        date=target_date,
                        available_slots=SLOTS,
                    )
                )

        existing_patients = (await session.execute(select(Patient))).scalars().all()
        if len(existing_patients) < 2:
            session.add_all(
                [
                    Patient(name="Rahul Verma", phone="+919999000111", preferred_language="hi"),
                    Patient(name="Kavin Raj", phone="+919999000222", preferred_language="ta"),
                ]
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
