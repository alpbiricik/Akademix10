import json
from pathlib import Path
import unittest
import threading
from unittest.mock import Mock, patch

from app.services.voice_poc_metrics import VoicePocMetrics
from app.services.voice_usage_service import SUMMARY_FIELDS, numeric_usage_summary, persist_voice_usage, schedule_voice_usage


class Phase4MetricsTests(unittest.TestCase):
    def setUp(self):
        self.metrics = VoicePocMetrics()
        self.addCleanup(self.metrics.close)

    def test_browser_first_token_and_retry_are_distinct(self):
        self.metrics.record("s", "state", "conversation_first_token", latency_ms=20)
        self.metrics.record("s", "state", "conversation", latency_ms=200)
        for event in ("browser_first_frame", "browser_playback", "browser_end_to_end"):
            self.metrics.record("s", "state", event, latency_ms=100)
        self.metrics.record("s", "state", "retry")
        self.metrics.record("s", "state", "cancel")
        snapshot = self.metrics.snapshot("s")
        self.assertEqual(snapshot["latency"]["conversation_first_token"]["p50_ms"], 20)
        self.assertEqual(snapshot["latency"]["conversation_response"]["p50_ms"], 200)
        self.assertEqual(snapshot["counts"]["cancel"], 1)
        self.assertEqual(snapshot["counts"]["retry"], 1)
        self.assertTrue(all(value is None for value in snapshot["provider_billing"].values()))

    def test_persistence_only_numeric_snapshot_and_no_content(self):
        self.metrics.record("s", "private state text", "tts", characters=20)
        snapshot = self.metrics.snapshot("s")
        snapshot["transcript"] = "private"
        result = numeric_usage_summary(snapshot)
        self.assertEqual(set(result), SUMMARY_FIELDS)
        self.assertNotIn("private", json.dumps(result))
        self.assertIsNone(result["actual_cost_usd"])
        client = Mock()
        client.rpc.return_value = True
        with patch("app.services.voice_usage_service.voice_poc_metrics", self.metrics):
            self.assertTrue(persist_voice_usage(client, "s"))
        self.assertEqual(client.rpc.call_args.args[0], "persist_voice_usage_summary")
        self.assertEqual(client.rpc.call_args.args[1]["p_summary"], result)

    def test_missing_migration_or_network_never_breaks_learning(self):
        self.metrics.record("s", "state", "error")
        client = Mock()
        client.rpc.side_effect = RuntimeError("private provider payload")
        with patch("app.services.voice_usage_service.voice_poc_metrics", self.metrics):
            self.assertFalse(persist_voice_usage(client, "s"))
            client.rpc.reset_mock()
            self.assertFalse(persist_voice_usage(client, "unknown"))
            client.rpc.assert_not_called()

    def test_invalid_aggregate_rejected(self):
        snapshot = self.metrics.snapshot("s")
        snapshot["usage"]["input_tokens"] = float("inf")
        with self.assertRaises(ValueError):
            numeric_usage_summary(snapshot)

    def test_migration_whitelist_matches_service_and_has_owner_guards(self):
        migration = Path(__file__).resolve().parents[3] / "supabase/migrations/0010_voice_usage_summary.sql"
        sql = migration.read_text()
        for key in SUMMARY_FIELDS:
            self.assertIn("'" + key + "'", sql)
        self.assertIn("session_row.learner_id <> auth.uid()", sql)
        self.assertIn("le.company_id = session_row.company_id", sql)
        self.assertIn("from public, anon", sql)
        self.assertNotIn("create policy", sql.lower())
        self.assertIn("Metrics must be numeric", sql)
        self.assertIn("u.role = 'learner' and u.status = 'active'", sql)
        self.assertIn("cm.company_id = session_row.company_id and cm.status = 'active'", sql)

    def test_scheduler_bounds_pending_tasks_and_releases_slots(self):
        executor = Mock()
        queued = []
        executor.submit.side_effect = lambda fn: queued.append(fn)
        with patch("app.services.voice_usage_service._usage_executor", executor), patch("app.services.voice_usage_service._usage_slots", threading.BoundedSemaphore(2)), patch("app.services.voice_usage_service.persist_voice_usage", return_value=False) as persist:
            self.assertTrue(schedule_voice_usage(Mock(), "one"))
            self.assertTrue(schedule_voice_usage(Mock(), "two"))
            self.assertFalse(schedule_voice_usage(Mock(), "three"))
            queued.pop(0)()
            self.assertTrue(schedule_voice_usage(Mock(), "three"))
            for task in queued:
                task()
            self.assertEqual(persist.call_count, 3)

    def test_scheduler_submit_failure_releases_slot(self):
        with patch("app.services.voice_usage_service._usage_executor") as executor, patch("app.services.voice_usage_service._usage_slots", threading.BoundedSemaphore(1)):
            executor.submit.side_effect = RuntimeError("closed")
            self.assertFalse(schedule_voice_usage(Mock(), "one"))
            executor.submit.side_effect = None
            self.assertTrue(schedule_voice_usage(Mock(), "two"))

