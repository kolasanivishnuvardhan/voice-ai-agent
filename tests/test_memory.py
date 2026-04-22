"""Tests for Redis-backed session and persistent memory behaviors."""

from __future__ import annotations

import asyncio

import pytest

from memory.persistent_memory import PersistentMemory
from memory.session_memory import SessionMemory


class FakeRedis:
    """Minimal async Redis stub for unit tests."""

    def __init__(self) -> None:
        self.kv: dict[str, tuple[str, int | None]] = {}
        self.hashes: dict[str, dict[str, str]] = {}

    async def get(self, key: str):
        if key not in self.kv:
            return None
        return self.kv[key][0].encode("utf-8")

    async def set(self, key: str, value: str, ex: int | None = None):
        self.kv[key] = (value, ex)

    async def delete(self, key: str):
        self.kv.pop(key, None)

    async def hgetall(self, key: str):
        mapping = self.hashes.get(key, {})
        return {k.encode("utf-8"): v.encode("utf-8") for k, v in mapping.items()}

    async def hset(self, key: str, mapping: dict[str, str]):
        self.hashes.setdefault(key, {}).update(mapping)

    async def expire(self, key: str, ttl: int):
        if key in self.kv:
            self.kv[key] = (self.kv[key][0], ttl)

    async def ttl(self, key: str):
        if key not in self.kv:
            return -1
        return self.kv[key][1] if self.kv[key][1] is not None else -1


@pytest.mark.asyncio
async def test_session_save_and_load() -> None:
    redis_client = FakeRedis()
    mem = SessionMemory(redis_client)
    state = mem._default_state("abc")
    state["pending_intent"] = "book"
    await mem.save_session("abc", state)

    loaded = await mem.load_session("abc")
    assert loaded["session_id"] == "abc"
    assert loaded["pending_intent"] == "book"


@pytest.mark.asyncio
async def test_persistent_memory_update() -> None:
    redis_client = FakeRedis()
    mem = PersistentMemory(redis_client)

    await mem.update_patient_memory("p1", {"preferred_language": "hi"})
    loaded = await mem.load_patient_memory("p1")
    assert loaded["preferred_language"] == "hi"


@pytest.mark.asyncio
async def test_session_ttl() -> None:
    redis_client = FakeRedis()
    mem = SessionMemory(redis_client)
    state = mem._default_state("ttlcase")
    await mem.save_session("ttlcase", state)

    ttl = await redis_client.ttl("session:ttlcase")
    assert ttl == mem.ttl_seconds
