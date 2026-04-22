"""Custom scheduler exceptions for appointment workflow validation."""

from __future__ import annotations


class SlotConflictError(Exception):
    """Raised when requested appointment slot is already booked."""


class PastDateError(Exception):
    """Raised when requested appointment date is in the past."""


class DoctorNotFoundError(Exception):
    """Raised when doctor lookup fails."""


class SlotNotAvailableError(Exception):
    """Raised when requested time is not in configured doctor schedule."""
