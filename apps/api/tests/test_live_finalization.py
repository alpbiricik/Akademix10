import threading
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from app.core.auth import Principal
from app.services import finalization_service as service
from app.services.conversation_cache import conversation_cache
from app.services.finalization_cache import finalization_cache
from app.services.finalization_service import FinalizeRequestDTO, FinalizationConflictError, FinalizationValidationError
from tests.fakes import mock_store
from tests.fakes.providers import DeterministicScoringProvider
from app.services import rubric_repository, scoring_service


class LiveFinalizationTests(unittest.TestCase):
    def setUp(self):
        conversation_cache.clear()
        finalization_cache.clear()
        self.session = deepcopy(mock_store.demo_session)
        self.state = deepcopy(next(s for s in mock_store.training_states if s.type == "roleplay"))
        self.state.completionRule = "answered"
        self.session.currentStateId = self.state.id
        self.principal = Principal(user_id=self.session.userId, role="learner", company_id=self.session.companyId, access_token="test")
        self.body = FinalizeRequestDTO(idempotencyKey="live-final-test", answers=[])
        self.client = MagicMock()
        self.client.select.return_value = []
        self.client.rpc.return_value = {"status": "completed", "evaluationId": "evaluation-1"}
        self.patches = [
            patch.object(service, "SupabaseUserClient", return_value=self.client),
            patch.object(service, "_load_session", return_value=self.session),
            patch.object(service, "_load_states", return_value=[self.state]),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(conversation_cache.clear)
        self.addCleanup(finalization_cache.clear)
        self.key = f"conversation:{self.session.id}:{self.state.id}"
        conversation_cache.put(self.key, {"turns": [
            {"learnerText": "I would ask about the delayed delivery.", "assistantText": "PRIVATE AVATAR WORDS"},
            {"learnerText": "We agree on support and a follow-up date.", "assistantText": "PRIVATE AVATAR WORDS"},
        ]}, 1800)
        self.result = scoring_service.score_answer(self.session, self.state, "A sufficiently detailed answer.",
            rubric_repository.get_rubric_for_state(self.session.templateId, self.state.id), provider=DeterministicScoringProvider(), enforce_query_limit=False)

    def test_all_live_learner_turns_scored_once_and_context_deleted_after_success(self):
        with patch.object(service.scoring_service, "score_answer", return_value=self.result) as score:
            result = service.finalize_session(self.session.id, self.body, self.principal)
        evidence = score.call_args.args[2]
        self.assertIn("delayed delivery", evidence)
        self.assertIn("follow-up date", evidence)
        self.assertNotIn("PRIVATE AVATAR WORDS", evidence)
        self.assertEqual(result.status, "completed")
        self.assertIsNone(conversation_cache.get(self.key))
        payload = self.client.rpc.call_args.args[1]
        self.assertNotIn("answerText", str(payload))
        self.assertNotIn("delayed delivery", str(payload))

    def test_persistence_failure_retry_reuses_scores_and_preserves_context(self):
        self.client.rpc.side_effect = [RuntimeError("unavailable"), {"status": "completed", "evaluationId": "evaluation-1"}]
        with patch.object(service.scoring_service, "score_answer", return_value=self.result) as score:
            with self.assertRaises(service.FinalizationError):
                service.finalize_session(self.session.id, self.body, self.principal)
            self.assertIsNotNone(conversation_cache.get(self.key))
            service.finalize_session(self.session.id, self.body, self.principal)
            self.assertEqual(score.call_count, 1)

    def test_expired_context_fails_without_empty_or_invented_score(self):
        conversation_cache.delete(self.key)
        with patch.object(service.scoring_service, "score_answer") as score:
            with self.assertRaises(FinalizationValidationError):
                service.finalize_session(self.session.id, self.body, self.principal)
            score.assert_not_called()
        self.assertIsNone(finalization_cache.get(f"finalization:{self.session.id}"))

    def test_three_full_live_turns_are_not_truncated_for_final_evaluation(self):
        texts = [str(index) + "a" * 1999 for index in range(3)]
        conversation_cache.put(self.key, {"turns": [{"learnerText": text} for text in texts]}, 1800)
        effective = service._with_live_answers(self.session.id, self.body, [self.state])
        service._validate_answers(effective, [self.state])
        self.assertEqual(effective.answers[0].answerText, "\n".join(texts))
        scoring_service.validate_answer(effective.answers[0].answerText, max_chars=service.DEFAULT_MAX_FINALIZE_ANSWER_CHARS)

    def test_completed_retry_reads_persisted_report_without_scoring(self):
        def select(table, query):
            if table == "session_evaluations":
                return [{"id": "evaluation-1", "status": "completed", "idempotency_key": self.body.idempotencyKey,
                         "payload_fingerprint": service._fingerprint(self.body)}]
            if table == "reports":
                return [{"overall_score": 80, "strengths": ["Clarity"]}]
            return []
        self.client.select.side_effect = select
        with patch.object(service.scoring_service, "score_answer") as score:
            response = service.finalize_session(self.session.id, self.body, self.principal)
            self.assertEqual(response.report["overallScore"], 80)
            score.assert_not_called()
            self.client.rpc.assert_not_called()

    def test_concurrent_requests_do_not_score_twice(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        def score(*args, **kwargs):
            entered.set()
            release.wait(3)
            return self.result
        def first():
            try:
                service.finalize_session(self.session.id, self.body, self.principal)
            except Exception as error:
                errors.append(error)
        with patch.object(service.scoring_service, "score_answer", side_effect=score) as scoring:
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                response = service.finalize_session(self.session.id, self.body, self.principal)
                self.assertEqual(response.status, "processing")
            finally:
                release.set()
                thread.join(3)
            self.assertEqual(scoring.call_count, 1)
            self.assertEqual(errors, [])

    def test_other_learner_cannot_access_cached_evidence(self):
        principal = Principal(user_id="other", role="learner", company_id=self.session.companyId, access_token="test")
        with self.assertRaises(FinalizationValidationError):
            service.finalize_session(self.session.id, self.body, principal)
        self.client.rpc.assert_not_called()

    def test_different_key_during_retry_is_rejected(self):
        finalization_cache.claim(f"finalization:{self.session.id}", {"key": "another", "fingerprint": service._fingerprint(self.body)}, 300)
        with self.assertRaises(FinalizationConflictError):
            service.finalize_session(self.session.id, self.body, self.principal)
