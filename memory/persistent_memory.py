"""Redis hash-backed persistent patient memory with rolling TTL."""

from __future__ import annotations

import os
from typing import Any

import redis.asyncio as redis


class PersistentMemory:
    """Stores long-lived patient preferences and interaction summary."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis: redis.Redis = redis_client
        self.ttl_seconds: int = int(os.getenv("PATIENT_MEMORY_TTL_DAYS", "30")) * 24 * 60 * 60

    def _key(self, patient_id: str) -> str:
        """Generate Redis key for a patient memory hash."""
        return f"patient:{patient_id}:memory"

    async def load_patient_memory(self, patient_id: str) -> dict[str, Any]:
        """Load patient memory hash and return decoded fields."""
        key: str = self._key(patient_id)
        raw: dict[bytes, bytes] = await self.redis.hgetall(key)
        if not raw:
            return {
                "preferred_language": "en",
                "preferred_doctor_id": "",
                "preferred_hospital": "",
                "last_appointment_date": "",
                "last_appointment_doctor": "",
                "appointment_count": "0",
                "notes": "",
            }
        decoded: dict[str, Any] = {k.decode("utf-8"): v.decode("utf-8") for k, v in raw.items()}
        return decoded

    async def update_patient_memory(self, patient_id: str, updates: dict[str, Any]) -> None:
        """Update patient memory hash and refresh TTL."""
        key: str = self._key(patient_id)
        normalized: dict[str, str] = {k: str(v) for k, v in updates.items()}
        if normalized:
            await self.redis.hset(key, mapping=normalized)
        await self.redis.expire(key, self.ttl_seconds)
