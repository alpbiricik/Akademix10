import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app.core import config
from app.services.conversation_cache import InMemoryConversationCache
from app.services.finalization_cache import InMemoryFinalizationCache


class CacheLifecycleTests(unittest.TestCase):
    def make_cache(self, cache_type=InMemoryConversationCache, **kwargs):
        cache = cache_type(**kwargs)
        self.addCleanup(cache.close)
        return cache

    def test_snapshots_do_not_expose_mutable_context(self):
        cache = self.make_cache()
        source = {"turns": [{"text": "answer"}]}
        cache.put("a", source, 30)
        source["turns"][0]["text"] = "changed"
        snapshot = cache.get("a")
        snapshot["turns"].clear()
        self.assertEqual(cache.get("a"), {"turns": [{"text": "answer"}]})

    def test_sweeper_removes_expired_data_without_reads(self):
        cache = self.make_cache(sweep_interval_seconds=0.01)
        cache.put("a", {"text": "ephemeral"}, 30)
        with cache._lock:
            cache._entries["a"].expires_at = time.time() - 1
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            with cache._lock:
                if not cache._entries:
                    break
            time.sleep(0.01)
        with cache._lock:
            self.assertFalse(cache._entries)

    def test_capacity_rejects_without_evicting_active_context(self):
        cache = self.make_cache(max_entries=1)
        cache.put("a", {}, 30)
        with self.assertRaises(RuntimeError):
            cache.put("b", {}, 30)
        self.assertEqual(cache.get("a"), {})
        cache._entries["a"].expires_at = 0
        cache.put("b", {}, 30)
        self.assertEqual(cache.get("b"), {})

    def test_prefix_touch_and_cleanup_isolate_sessions(self):
        cache = self.make_cache()
        for key in ("session:1:a", "session:1:b", "session:10:a"):
            cache.put(key, {}, 30)
        other_expiry = cache._entries["session:10:a"].expires_at
        cache.touch_prefix("session:1:", 60)
        self.assertGreater(cache._entries["session:1:a"].expires_at, other_expiry)
        self.assertEqual(cache._entries["session:10:a"].expires_at, other_expiry)
        cache.delete_prefix("session:1:")
        self.assertIsNone(cache.get("session:1:a"))
        self.assertEqual(cache.get("session:10:a"), {})

    def test_only_one_concurrent_claim_and_payload_is_protected(self):
        cache = self.make_cache(InMemoryFinalizationCache)
        barrier = threading.Barrier(8)
        def claim(index):
            barrier.wait()
            return cache.claim("session", {"fingerprint": str(index)}, 30)
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(claim, range(8))), 1)
        original = cache.get("session")
        with self.assertRaises(RuntimeError):
            cache.put("session", {"fingerprint": "replacement"}, 30)
        self.assertEqual(cache.get("session"), original)
        cache.update_claim("session", {**original, "scored": True})
        self.assertFalse(cache.claim("session", {}, 30))
        cache.release("session")
        self.assertTrue(cache.get("session")["scored"])
        self.assertTrue(cache.claim("session", {}, 30))

    def test_close_discards_data_and_stops_worker(self):
        cache = self.make_cache()
        cache.put("a", {}, 30)
        cache.close()
        self.assertFalse(cache._sweeper.is_alive())
        self.assertIsNone(cache.get("a"))
        with self.assertRaises(RuntimeError):
            cache.put("a", {}, 30)

    def test_expired_owner_cannot_modify_new_lease(self):
        cache = self.make_cache(InMemoryFinalizationCache)
        self.assertTrue(cache.claim("session", {"owner": "old"}, 30))
        cache._entries["session"].expires_at = 0
        self.assertTrue(cache.claim("session", {"owner": "new"}, 30))
        with self.assertRaises(RuntimeError):
            cache.update_claim("session", {"owner": "old", "scored": True})
        self.assertFalse(cache.renew_claim("session", "old", 60))
        self.assertFalse(cache.release_claim("session", "old"))
        self.assertFalse(cache.release_claim("session", "old", delete=True))
        self.assertEqual(cache.get("session"), {"owner": "new"})
        self.assertFalse(cache.claim("session", {}, 30))
        self.assertTrue(cache.renew_claim("session", "new", 60))
        self.assertGreater(cache._entries["session"].expires_at, time.time() + 59)
        cache.update_claim("session", {"owner": "new", "scored": True})
        self.assertTrue(cache.release_claim("session", "new"))
        self.assertTrue(cache.get("session")["scored"])
        self.assertTrue(cache.claim("session", {"owner": "third"}, 30))
        self.assertTrue(cache.release_claim("session", "third", delete=True))
        self.assertIsNone(cache.get("session"))

    def test_renewal_cannot_resurrect_expired_claim(self):
        cache = self.make_cache(InMemoryFinalizationCache)
        cache.claim("session", {"owner": "old"}, 30)
        cache._entries["session"].expires_at = 0
        self.assertFalse(cache.renew_claim("session", "old", 60))
        self.assertIsNone(cache.get("session"))

    def test_ttl_config_requires_positive_explicit_production_value(self):
        with patch.dict(config.os.environ, {}, clear=True):
            with patch.object(config, "APP_ENV", "local"):
                self.assertEqual(config._conversation_context_ttl(), 1800)
            with patch.object(config, "APP_ENV", "production"):
                with self.assertRaises(ValueError):
                    config._conversation_context_ttl()
            for value in ("0", "-5", "bad", ""):
                with patch.dict(config.os.environ, {"CONVERSATION_CONTEXT_TTL_SECONDS": value}):
                    with self.assertRaises(ValueError):
                        config._conversation_context_ttl()
            with patch.dict(config.os.environ, {"CONVERSATION_CONTEXT_TTL_SECONDS": "90"}):
                self.assertEqual(config._conversation_context_ttl(), 90)


if __name__ == "__main__":
    unittest.main()
