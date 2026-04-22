"""Health and latency monitoring endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health(request: Request) -> dict[str, Any]:
    """Basic service health report."""
    return {
        "status": "ok",
        "whisper_model": request.app.state.stt_service.model_name,
        "latency_events": len(request.app.state.latency_stats),
    }


@router.get("/latency")
async def latency(request: Request) -> dict[str, Any]:
    """Return recent latency logs."""
    entries: list[dict[str, Any]] = request.app.state.latency_stats
    avg_total: float = (
        sum(item["total_ms"] for item in entries) / len(entries) if entries else 0.0
    )
    return {"count": len(entries), "average_total_ms": round(avg_total, 2), "recent": entries[-20:]}
