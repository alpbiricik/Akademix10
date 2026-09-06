import unittest
from copy import deepcopy

from app.schemas.dtos import DimensionScoreDTO, ProviderMetadataDTO, ProviderScoringResponseDTO
from app.services import rubric_repository, scoring_repository, scoring_service, session_engine
from app.services.ai_provider import MAX_QUERIES_PER_STATE
from app.services.scoring_errors import AnswerGuardrailError, InvalidRubricError, MaxQueriesPerStateError, ProviderRetryExhaustedError
from tests.fakes import mock_store
from tests.fakes.providers import DeterministicScoringProvider as MockScoringProvider


class MalformedProvider:
    provider_name = "malformed"

    def score(self, request):
        return ProviderScoringResponseDTO(
            dimensionScores=[DimensionScoreDTO(dimensionId="wrong", name="Wrong", score=50, rationale="bad")],
            conciseLearnerFeedback="bad",
            strengths=[],
            improvementAreas=[],
            recommendedNextAction="retry_state",
            providerMetadata=ProviderMetadataDTO(provider="malformed", model="bad"),
        )


class FlakyProvider:
    provider_name = "flaky"

    def __init__(self):
        self.calls = 0

    def score(self, request):
        self.calls += 1
        if self.calls == 1:
            return {"dimensionScores": []}
        return MockScoringProvider().score(request)


class ScoringServiceTests(unittest.TestCase):
    def setUp(self):
        scoring_repository.reset_scoring_store()
        self.session = deepcopy(mock_store.demo_session)
        self.state = mock_store.training_states[3]
        self.rubric = rubric_repository.get_rubric_for_state(self.session.templateId, self.state.id)
        self.answer = "I understand the renewal concern. What outcome would make the platform feel worth the investment?"
        self.provider = MockScoringProvider()

    def test_valid_rubric_validation(self):
        scoring_service.validate_rubric(self.rubric)

    def test_invalid_weights(self):
        rubric = deepcopy(self.rubric)
        rubric.dimensions[0].weight = 0.5
        with self.assertRaises(InvalidRubricError):
            scoring_service.validate_rubric(rubric)

    def test_score_range_validation(self):
        response = MockScoringProvider().score(scoring_service.ProviderRequestDTO(sessionId=self.session.id, stateId=self.state.id, answerRef="a", answerText=self.answer, statePrompt=self.state.prompt, rubric=self.rubric, maxQueriesPerState=3))
        response.dimensionScores[0].score = 101
        with self.assertRaises(Exception):
            scoring_service.validate_provider_output(self.rubric, response)

    def test_weighted_overall_score(self):
        scores = [
            DimensionScoreDTO(dimensionId="clarity", name="Clarity", score=80, rationale=""),
            DimensionScoreDTO(dimensionId="empathy", name="Empathy", score=60, rationale=""),
            DimensionScoreDTO(dimensionId="structure", name="Structure", score=100, rationale=""),
            DimensionScoreDTO(dimensionId="confidence", name="Confidence", score=70, rationale=""),
        ]
        self.assertEqual(scoring_service.calculate_overall_score(self.rubric, scores), 78)

    def test_deterministic_mock_provider(self):
        first = scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)
        scoring_repository.reset_scoring_store()
        second = scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)
        self.assertEqual(first.overallScore, second.overallScore)
        self.assertEqual(first.dimensionScores, second.dimensionScores)

    def test_malformed_provider_output_and_retry_limit(self):
        with self.assertRaises(ProviderRetryExhaustedError):
            scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=MalformedProvider())

    def test_retry_limit_allows_later_valid_output(self):
        result = scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=FlakyProvider())
        self.assertEqual(result.providerMetadata.attemptCount, 2)

    def test_max_queries_per_state(self):
        for _ in range(MAX_QUERIES_PER_STATE):
            scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)
        with self.assertRaises(MaxQueriesPerStateError):
            scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)

    def test_empty_and_oversized_answer_guardrails(self):
        with self.assertRaises(AnswerGuardrailError):
            scoring_service.score_answer(self.session, self.state, " ", self.rubric, provider=self.provider)
        with self.assertRaises(AnswerGuardrailError):
            scoring_service.score_answer(self.session, self.state, "x" * 5001, self.rubric, provider=self.provider)

    def test_skill_impact_calculation(self):
        result = scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)
        skills = {impact.skill for impact in result.skillImpacts}
        self.assertIn("Communication", skills)
        self.assertTrue(all(impact.delta >= 1 for impact in result.skillImpacts))

    def test_existing_answer_session_flow_backward_compatibility(self):
        result = scoring_service.score_answer(self.session, self.state, self.answer, self.rubric, provider=self.provider)
        updated = session_engine.apply_scoring_result(self.session, result)
        self.assertEqual(updated.feedback[0].overallScore, result.overallScore)
        self.assertTrue(updated.skillScores)


if __name__ == "__main__":
    unittest.main()
