"""Models package exports."""

from models.appointment import Appointment
from models.availability import DoctorSchedule
from models.doctor import Doctor
from models.patient import Patient

__all__: list[str] = ["Patient", "Doctor", "DoctorSchedule", "Appointment"]
