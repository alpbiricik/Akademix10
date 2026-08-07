import os
import time
import unittest
from copy import deepcopy

from app.routers.learner import _scoring_results_from_supabase
from app.core.auth import Principal
from app.services import finalization_service, mock_store, rubric_repository, scoring_repository, scoring_service
from app.services.ai_provider import MAX_QUERIES_PER_STATE
from app.services.finalization_cache import InMemoryFinalizationCache, finalization_cache
from app.services.finalization_service import (
    FINALIZE_CONTRACT_VERSION,
    FinalizationConflictError,
    FinalizationValidationError,
    FinalizeAnswerDTO,
    FinalizeRequestDTO,
    _validate_answers,
    finalize_session,
)


class FakeSupabaseClient:
    def select(self, table: str, query: str):
        self.last_query = query
        if table == "session_feedback":
            return [
                {
                    "state_id": "state-1",
                    "overall_score": 82,
                    "dimensions": [{"label": "Clarity", "score": 84}, {"label": "Empathy", "score": 80}],
                    "feedback_text": "Clear and useful feedback.",
                    "improvement_suggestion": "Ask one more discovery question.",
                    "next_action": "review_feedback",
                    "provider": "mock",
                    "model_name": "mock-v1",
                    "metadata": {
                        "schemaVersion": "1.0",
                        "rubricId": "rubric-1",
                        "rubricVersion": "2026-08-01",
                        "guardrailFlags": [],
                    },
                    "created_at": "2026-08-07T10:00:00Z",
                }
            ]
        if table == "skill_scores":
            return [{"state_id": "state-1", "skill": "Communication", "score": 83, "delta": 2}]
        return []


class ConflictSupabaseClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def select(self, table: str, query: str):
        if table == "training_sessions":
            return [
                {
                    "id": "session-1",
                    "module_id": "communication-sales-101",
                    "template_id": "template-sales-communication",
                    "learner_id": "learner-1",
                    "company_id": "company-1",
                    "current_state_id": "state-1",
                    "completed_state_ids": [],
                    "status": "in_progress",
                    "started_at": "2026-08-07T10:00:00Z",
                    "updated_at": "2026-08-07T10:00:00Z",
                    "completed_at": None,
                }
            ]
        if table == "session_usage":
            return []
        if table == "session_evaluations":
            return [{"id": "evaluation-1", "status": "completed", "payload_fingerprint": "different"}]
        return []


class FinalizationContractTests(unittest.TestCase):
    def setUp(self):
        scoring_repository.reset_mock_scoring_store()
        finalization_cache.clear()
        self.states = deepcopy(mock_store.training_states)
        self.answered_state = next(state for state in self.states if state.completionRule == "answered")

    def request_for_answered_states(self) -> FinalizeRequestDTO:
        return FinalizeRequestDTO(
            idempotencyKey="unit-test-key",
            contractVersion=FINALIZE_CONTRACT_VERSION,
            answers=[
                FinalizeAnswerDTO(stateId=state.id, answerText="This answer is long enough for deterministic scoring.")
                for state in self.states
                if state.completionRule == "answered"
            ],
        )

    def test_validation_rejects_duplicate_missing_and_oversized_answers(self):
        valid = self.request_for_answered_states()
        duplicate = valid.model_copy(
            update={"answers": valid.answers + [FinalizeAnswerDTO(stateId=valid.answers[0].stateId, answerText="Duplicate answer text.")]}
        )
        with self.assertRaises(FinalizationValidationError):
            _validate_answers(duplicate, self.states)

        missing = valid.model_copy(update={"answers": valid.answers[:-1]})
        with self.assertRaises(FinalizationValidationError):
            _validate_answers(missing, self.states)

        old_limit = os.environ.get("FINALIZATION_MAX_ANSWER_CHARS")
        os.environ["FINALIZATION_MAX_ANSWER_CHARS"] = "8"
        try:
            with self.assertRaises(FinalizationValidationError):
                _validate_answers(valid, self.states)
        finally:
            if old_limit is None:
                os.environ.pop("FINALIZATION_MAX_ANSWER_CHARS", None)
            else:
                os.environ["FINALIZATION_MAX_ANSWER_CHARS"] = old_limit

    def test_cache_claim_ttl_release_and_delete(self):
        cache = InMemoryFinalizationCache()
        self.assertTrue(cache.claim("finalization:session:key", {"fingerprint": "a"}, ttl_seconds=30))
        self.assertFalse(cache.claim("finalization:session:key", {"fingerprint": "a"}, ttl_seconds=30))
        cache.release("finalization:session:key")
        self.assertEqual(cache.get("finalization:session:key"), {"fingerprint": "a"})
        cache._entries["finalization:session:key"].expires_at = time.time() - 1
        self.assertIsNone(cache.get("finalization:session:key"))
        cache.put("finalization:session:key", {"fingerprint": "b"}, ttl_seconds=30)
        cache.delete("finalization:session:key")
        self.assertIsNone(cache.get("finalization:session:key"))

    def test_finalize_scoring_can_bypass_legacy_per_state_query_limit(self):
        session = deepcopy(mock_store.demo_session)
        rubric = rubric_repository.get_rubric_for_state(session.templateId, self.answered_state.id)
        for _ in range(MAX_QUERIES_PER_STATE):
            scoring_service.score_answer(session, self.answered_state, "This answer is enough to score.", rubric)
        result = scoring_service.score_answer(
            session,
            self.answered_state,
            "This final batch answer is enough to score.",
            rubric,
            enforce_query_limit=False,
        )
        self.assertEqual(result.sessionId, session.id)

    def test_supabase_scoring_results_are_reconstructed_without_raw_answer(self):
        results = _scoring_results_from_supabase(FakeSupabaseClient(), "session-1")
        self.assertEqual(len(results), 1)
        result = results[0]
        rendered = result.model_dump_json()
        self.assertEqual(result.rubricVersion, "2026-08-01")
        self.assertEqual(result.providerMetadata.provider, "mock")
        self.assertEqual(result.skillImpacts[0].skill, "Communication")
        self.assertNotIn("learner raw answer", rendered)

    def test_same_idempotency_key_different_payload_raises_conflict_before_validation(self):
        original_client = finalization_service.SupabaseUserClient
        finalization_service.SupabaseUserClient = ConflictSupabaseClient
        try:
            with self.assertRaises(FinalizationConflictError):
                finalize_session(
                    "session-1",
                    FinalizeRequestDTO(
                        idempotencyKey="existing-key",
                        contractVersion=FINALIZE_CONTRACT_VERSION,
                        answers=[FinalizeAnswerDTO(stateId="missing-state", answerText="Different payload text.")],
                    ),
                    Principal(user_id="learner-1", role="learner", company_id="company-1", access_token="token"),
                )
        finally:
            finalization_service.SupabaseUserClient = original_client


if __name__ == "__main__":
    unittest.main()
