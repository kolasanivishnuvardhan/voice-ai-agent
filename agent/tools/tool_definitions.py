"""OpenAI-compatible tool schemas for Groq function calling."""

from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "checkAvailability",
            "description": "Check doctor slot availability by specialization and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_specialization": {"type": "string"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD"},
                },
                "required": ["doctor_specialization", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bookAppointment",
            "description": "Book an appointment for a patient and doctor at date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "doctor_id": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string", "description": "HH:MM"},
                },
                "required": ["patient_id", "doctor_id", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelAppointment",
            "description": "Cancel an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rescheduleAppointment",
            "description": "Reschedule an appointment to a new date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "new_date": {"type": "string"},
                    "new_time": {"type": "string"},
                },
                "required": ["appointment_id", "new_date", "new_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getPatientHistory",
            "description": "Get a patient's recent appointment history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                },
                "required": ["patient_id"],
            },
        },
    },
]
