import copy
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.services.conversation_cache import ConversationCache, InMemoryConversationCache


class FinalizationCache(ConversationCache, Protocol):
    """claim must atomically acquire a key with TTL (e.g. Redis SET NX EX).

    put must never replace a live claim; remote implementations must preserve
    this condition atomically too. Callers use one key per session.
    """

    def claim(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> bool: ...
    def release(self, key: str) -> None: ...
    def update_claim(self, key: str, payload: dict[str, Any]) -> None: ...
    def renew_claim(self, key: str, owner: str, ttl_seconds: int) -> bool: ...
    def release_claim(self, key: str, owner: str, delete: bool = False) -> bool: ...


@dataclass
class CacheEntry:
    payload: dict[str, Any]
    expires_at: float
    in_flight: bool = False


class InMemoryFinalizationCache(InMemoryConversationCache):
    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            self._prepare_write(key, ttl_seconds)
            entry = self._entries.get(key)
            if entry and entry.in_flight:
                raise RuntimeError("Cannot overwrite an active finalization claim")
            self._entries[key] = CacheEntry(copy.deepcopy(payload), time.time() + ttl_seconds)

    def claim(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> bool:
        with self._lock:
            self._prepare_write(key, ttl_seconds)
            entry = self._entries.get(key)
            if entry and entry.in_flight:
                return False
            self._entries[key] = CacheEntry(copy.deepcopy(payload), time.time() + ttl_seconds, True)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            if entry:
                entry.in_flight = False

    def update_claim(self, key: str, payload: dict[str, Any]) -> None:
        """Only the caller holding the claim may update its retry snapshot."""
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            if not entry or not entry.in_flight:
                raise RuntimeError("Finalization claim is no longer active")
            if entry.payload.get("owner") is not None and entry.payload["owner"] != payload.get("owner"):
                raise RuntimeError("Finalization claim ownership changed")
            entry.payload = copy.deepcopy(payload)

    def renew_claim(self, key: str, owner: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive")
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            if not entry or not entry.in_flight or entry.payload.get("owner") != owner:
                return False
            entry.expires_at = time.time() + ttl_seconds
            return True

    def release_claim(self, key: str, owner: str, delete: bool = False) -> bool:
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            if not entry or not entry.in_flight or entry.payload.get("owner") != owner:
                return False
            if delete:
                del self._entries[key]
            else:
                entry.in_flight = False
            return True


finalization_cache = InMemoryFinalizationCache()
