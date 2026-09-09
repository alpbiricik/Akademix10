import copy
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol


class ConversationCache(Protocol):
    """Backend-neutral TTL contract; remote implementations must return snapshots."""

    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None: ...
    def get(self, key: str) -> dict[str, Any] | None: ...
    def delete(self, key: str) -> None: ...
    def delete_prefix(self, prefix: str) -> None: ...
    def touch_prefix(self, prefix: str, ttl_seconds: int) -> None: ...
    def clear(self) -> None: ...


@dataclass
class ConversationCacheEntry:
    payload: dict[str, Any]
    expires_at: float


class InMemoryConversationCache:
    def __init__(self, max_entries: int = 1024, sweep_interval_seconds: float = 1.0) -> None:
        if max_entries <= 0 or sweep_interval_seconds <= 0:
            raise ValueError("Cache bounds and cleanup interval must be positive")
        self._entries: dict[str, ConversationCacheEntry] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries
        self._stop = threading.Event()
        self._sweeper = threading.Thread(
            target=self._sweep, args=(sweep_interval_seconds,), daemon=True,
            name="ephemeral-cache-cleanup",
        )
        self._sweeper.start()

    def _sweep(self, interval: float) -> None:
        while not self._stop.wait(interval):
            with self._lock:
                self._purge_expired()

    def _purge_expired(self) -> None:
        now = time.time()
        for key in [key for key, entry in self._entries.items() if entry.expires_at <= now]:
            del self._entries[key]

    def _prepare_write(self, key: str, ttl_seconds: int) -> None:
        if self._stop.is_set():
            raise RuntimeError("Cache is closed")
        if ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive")
        self._purge_expired()
        if key not in self._entries and len(self._entries) >= self._max_entries:
            raise RuntimeError("Ephemeral cache capacity reached")

    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            self._prepare_write(key, ttl_seconds)
            self._entries[key] = ConversationCacheEntry(copy.deepcopy(payload), time.time() + ttl_seconds)

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            return copy.deepcopy(entry.payload) if entry else None

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [key for key in self._entries if key.startswith(prefix)]:
                del self._entries[key]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def touch_prefix(self, prefix: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive")
        with self._lock:
            self._purge_expired()
            expires_at = time.time() + ttl_seconds
            for key, entry in self._entries.items():
                if key.startswith(prefix):
                    entry.expires_at = expires_at

    def close(self) -> None:
        self._stop.set()
        self._sweeper.join(timeout=2)
        self.clear()


conversation_cache = InMemoryConversationCache()
