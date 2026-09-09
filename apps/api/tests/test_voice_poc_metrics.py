import json
import unittest
from unittest.mock import patch

from app.services.voice_poc_metrics import VoicePocMetrics, RATE_ENV


class VoicePocMetricsTests(unittest.TestCase):
    def setUp(self):
        self.metrics = VoicePocMetrics(max_observations=100)
        self.addCleanup(self.metrics.close)

    def test_numeric_latency_usage_and_unknown_cost(self):
        self.metrics.record("session", "state", "conversation", latency_ms=100, input_tokens=1000, output_tokens=200)
        self.metrics.record("session", "state", "conversation", latency_ms=300)
        with patch.dict("os.environ", {}, clear=True):
            result = self.metrics.snapshot("session")
        self.assertEqual(result["latency"]["conversation_response"]["p50_ms"], 200)
        self.assertEqual(result["usage"]["input_tokens"], 1000)
        self.assertIsNone(result["cost_usd"]["total"])
        self.assertEqual(result["live_gate"]["decision"], "INSUFFICIENT_MEASUREMENTS")

    def test_transcripts_keys_payloads_and_invalid_numbers_rejected(self):
        for metrics in ({"transcript": "private"}, {"latency_ms": "private"}, {"latency_ms": float("nan")}, {"latency_ms": -1}):
            with self.assertRaises(ValueError):
                self.metrics.record("session", "state", "conversation", **metrics)
        self.assertNotIn("private", json.dumps(self.metrics.snapshot("session")))

    def test_sessions_isolated_and_ttl_clears_measurements(self):
        self.metrics.record("one", "state", "avatar_start")
        self.assertEqual(self.metrics.snapshot("two")["counts"]["avatar_start"], 0)
        self.metrics._cache._entries["one"].expires_at = 0
        self.assertEqual(self.metrics.snapshot("one")["counts"]["avatar_start"], 0)

    def test_minimum_counts_are_not_an_automatic_go(self):
        for _ in range(10):
            self.metrics.record("session", "state", "avatar_start")
            self.metrics.record("session", "state", "avatar_stop", duration_seconds=42)
        self.metrics.record("session", "state", "stt", latency_ms=50, audio_seconds=30)
        self.metrics.record("session", "state", "stt_partial", latency_ms=20)
        self.metrics.record("session", "state", "conversation", latency_ms=100)
        self.metrics.record("session", "state", "tts", first_audio_ms=20, characters=100)
        self.metrics.record("session", "state", "avatar_delivery", latency_ms=400)
        with patch.dict("os.environ", {env: "1" for env, _ in RATE_ENV.values()}):
            result = self.metrics.snapshot("session")
        self.assertTrue(result["live_gate"]["minimum_measurements_met"])
        self.assertEqual(result["live_gate"]["decision"], "MANUAL_REVIEW_REQUIRED")
        self.assertIsNotNone(result["cost_usd"]["total"])
