import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ConversationCacheEntry:
    payload: dict[str, Any]
    expires_at: float


class InMemoryConversationCache:
    def __init__(self) -> None:
        self._entries: dict[str, ConversationCacheEntry] = {}

    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        self._entries[key] = ConversationCacheEntry(payload=payload, expires_at=time.time() + ttl_seconds)

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

    def clear(self) -> None:
        self._entries.clear()


conversation_cache = InMemoryConversationCache()
