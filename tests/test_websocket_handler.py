"""Focused tests for websocket handler extraction helpers."""

from __future__ import annotations

from backend.websocket.handler import _extract_contextual_slot_choice, _extract_time_slot


def test_extract_time_slot_with_am_pm_text() -> None:
    assert _extract_time_slot("Book at 9 am") == "09:00"


def test_extract_contextual_slot_choice_with_single_digit() -> None:
    slots = ["09:00", "10:30", "12:00"]
    assert _extract_contextual_slot_choice("9", slots) == "09:00"


def test_extract_contextual_slot_choice_with_oclock() -> None:
    slots = ["09:00", "10:30", "12:00"]
    assert _extract_contextual_slot_choice("Book for 9 o'clock", slots) == "09:00"


def test_extract_contextual_slot_choice_no_match() -> None:
    slots = ["10:30", "12:00"]
    assert _extract_contextual_slot_choice("9", slots) is None
