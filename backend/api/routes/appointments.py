"""Appointment API routes for CRUD-like scheduling operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.controllers.appointment_controller import AppointmentController
from memory.persistent_memory import PersistentMemory
from models.database import get_db_session
from scheduler.appointment_engine import AppointmentEngine
from scheduler.exceptions import DoctorNotFoundError, PastDateError, SlotConflictError, SlotNotAvailableError

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


class BookRequest(BaseModel):
    """Book request schema."""

    patient_id: str
    doctor_id: str
    date: str
    time: str


class RescheduleRequest(BaseModel):
    """Reschedule request schema."""

    appointment_id: str
    new_date: str
    new_time: str


def _controller(db: AsyncSession, memory: PersistentMemory) -> AppointmentController:
    """Construct appointment controller dependency."""
    return AppointmentController(AppointmentEngine(db, memory))


def _get_persistent_memory(request: Request) -> PersistentMemory:
    """Resolve persistent memory from FastAPI app state."""
    return request.app.state.persistent_memory


@router.get("/availability")
async def check_availability(
    specialization: str,
    date: str,
    db: AsyncSession = Depends(get_db_session),
    memory: PersistentMemory = Depends(_get_persistent_memory),
) -> list[dict[str, Any]]:
    """Check appointment availability."""
    controller = _controller(db, memory)
    return await controller.check_availability(specialization, date)


@router.post("/book")
async def book_appointment(
    request: BookRequest,
    db: AsyncSession = Depends(get_db_session),
    memory: PersistentMemory = Depends(_get_persistent_memory),
) -> dict[str, Any]:
    """Book appointment endpoint."""
    controller = _controller(db, memory)
    try:
        return await controller.book_appointment(request.model_dump())
    except (PastDateError, DoctorNotFoundError, SlotNotAvailableError, SlotConflictError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cancel/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db_session),
    memory: PersistentMemory = Depends(_get_persistent_memory),
) -> dict[str, Any]:
    """Cancel appointment endpoint."""
    controller = _controller(db, memory)
    try:
        return await controller.cancel_appointment(appointment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reschedule")
async def reschedule_appointment(
    request: RescheduleRequest,
    db: AsyncSession = Depends(get_db_session),
    memory: PersistentMemory = Depends(_get_persistent_memory),
) -> dict[str, Any]:
    """Reschedule appointment endpoint."""
    controller = _controller(db, memory)
    try:
        return await controller.reschedule_appointment(request.model_dump())
    except (PastDateError, DoctorNotFoundError, SlotNotAvailableError, SlotConflictError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history/{patient_id}")
async def patient_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db_session),
    memory: PersistentMemory = Depends(_get_persistent_memory),
) -> list[dict[str, Any]]:
    """Patient history endpoint."""
    controller = _controller(db, memory)
    return await controller.get_patient_history(patient_id)
