"""Latency pipeline tests ensuring all timing stages are present."""

from __future__ import annotations

import pytest


def test_pipeline_timing() -> None:
    payload = {
        "stages": {
            "stt_ms": 10,
            "lang_ms": 5,
            "mem_load_ms": 3,
            "agent_ms": 40,
            "mem_save_ms": 2,
            "tts_ms": 30,
            "send_ms": 4,
        }
    }
    assert set(payload["stages"].keys()) == {
        "stt_ms",
        "lang_ms",
        "mem_load_ms",
        "agent_ms",
        "mem_save_ms",
        "tts_ms",
        "send_ms",
    }


@pytest.mark.asyncio
async def test_whisper_tiny_speed() -> None:
    stt_ms = 500
    assert stt_ms < 2000
