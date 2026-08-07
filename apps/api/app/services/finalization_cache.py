import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    payload: dict[str, Any]
    expires_at: float
    in_flight: bool = False


class InMemoryFinalizationCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        self._entries[key] = CacheEntry(payload=payload, expires_at=time.time() + ttl_seconds)

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.expires_at <= time.time():
            del self._entries[key]
            return None
        return entry.payload

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    def claim(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> bool:
        entry = self._entries.get(key)
        if entry and entry.expires_at > time.time() and entry.in_flight:
            return False
        self._entries[key] = CacheEntry(payload=payload, expires_at=time.time() + ttl_seconds, in_flight=True)
        return True

    def release(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry:
            entry.in_flight = False

    def clear(self) -> None:
        self._entries.clear()


finalization_cache = InMemoryFinalizationCache()
