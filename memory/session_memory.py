"""Redis-backed session memory with 1-hour TTL for conversational context."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis


class SessionMemory:
    """Manages per-session conversational state in Redis."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis: redis.Redis = redis_client
        self.ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

    def _default_state(self, session_id: str) -> dict[str, Any]:
        """Construct a default session payload."""
        # Use first existing patient; if none, create temporary UUID (will be mapped later)
        # Hardcoded to first test patient for now:
        SAMPLE_PATIENT_ID = "96c5f10f-e610-428a-ac99-4e4291c50918"  # Rahul Verma
        
        return {
            "session_id": session_id,
            "patient_id": SAMPLE_PATIENT_ID,
            "language": "en",
            "preferred_language": "en",
            "conversation_history": [],
            "pending_intent": None,
            "pending_details": {
                "specialization": None,
                "date": None,
                "time": None,
                "doctor_id": None,
                "available_slots": [],
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def load_session(self, session_id: str) -> dict[str, Any]:
        """Load session state from Redis, creating defaults if absent."""
        key: str = f"session:{session_id}"
        raw: bytes | None = await self.redis.get(key)
        if raw is None:
            default_state: dict[str, Any] = self._default_state(session_id)
            await self.save_session(session_id, default_state)
            return default_state

        state: dict[str, Any] = json.loads(raw.decode("utf-8"))
        return state

    async def save_session(self, session_id: str, state: dict[str, Any]) -> None:
        """Persist session state with TTL refresh."""
        key: str = f"session:{session_id}"
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        await self.redis.set(key, json.dumps(state), ex=self.ttl_seconds)

    async def clear_session(self, session_id: str) -> None:
        """Delete a session payload from Redis."""
        key: str = f"session:{session_id}"
        await self.redis.delete(key)
