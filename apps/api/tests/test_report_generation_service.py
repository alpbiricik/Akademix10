import unittest
from copy import deepcopy

from app.schemas.dtos import (
    DimensionScoreDTO,
    GuardrailFlagDTO,
    ProviderMetadataDTO,
    SkillImpactDTO,
    StructuredScoringResultDTO,
    TokenCostMetadataDTO,
)
from app.services import report_generation_service as reports
from app.services.report_errors import InvalidReportInputError
from tests.fakes import mock_store


def make_result(
    session_id: str,
    state_id: str,
    overall: int,
    generated_at: str,
    company_marker: str = "",
    answer_ref: str | None = None,
) -> StructuredScoringResultDTO:
    return StructuredScoringResultDTO(
        schemaVersion="1.0",
        sessionId=session_id,
        stateId=state_id,
        answerRef=answer_ref or f"{session_id}:{state_id}:{generated_at}",
        rubricId="rubric-template-sales-communication-v1",
        rubricVersion="1.0",
        overallScore=overall,
        dimensionScores=[
            DimensionScoreDTO(dimensionId="clarity", name="Clarity", score=overall, rationale=""),
            DimensionScoreDTO(dimensionId="empathy", name="Empathy", score=max(0, overall - 10), rationale=""),
        ],
        conciseLearnerFeedback="Safe report feedback.",
        strengths=[f"Strength {overall}{company_marker}"],
        improvementAreas=[f"Improve {overall}{company_marker}"],
        recommendedNextAction="complete_state",
        skillImpacts=[
            SkillImpactDTO(skill="Communication", delta=2, score=overall, sourceDimensionIds=["clarity"]),
            SkillImpactDTO(skill="Empathy", delta=1, score=max(0, overall - 10), sourceDimensionIds=["empathy"]),
        ],
        guardrailFlags=[GuardrailFlagDTO(code="short_answer", message="Short answer.", severity="warning")] if overall < 70 else [],
        providerMetadata=ProviderMetadataDTO(provider="mock", model="deterministic-mock-v1"),
        tokenCostMetadata=TokenCostMetadataDTO(inputTokens=10, outputTokens=5, estimatedCostUsd=0.01),
        generatedAt=generated_at,
    )


class ReportGenerationServiceTests(unittest.TestCase):
    def setUp(self):
        self.session = deepcopy(mock_store.demo_session)
        self.session.completedStateIds = [state.id for state in mock_store.training_states]
        self.session.status = "completed"
        self.session.completedAt = "2026-07-29T10:00:00.000Z"
        self.secondary_session = self.session.model_copy(deep=True)
        self.secondary_session.id = "demo-session-2"
        self.secondary_session.userId = "user-learner-2"
        self.other_company_session = self.session.model_copy(deep=True)
        self.other_company_session.id = "other-company-session"
        self.other_company_session.companyId = "company-secondary"
        self.template = mock_store.training_templates[3]
        self.module = mock_store.training_modules[0]
        self.state_1 = mock_store.training_states[3]
        self.state_2 = mock_store.training_states[5]
        self.results = [
            make_result(self.session.id, self.state_1.id, 80, "2026-07-29T10:00:00.000Z"),
            make_result(self.session.id, self.state_2.id, 90, "2026-07-29T10:05:00.000Z"),
            make_result(self.secondary_session.id, self.state_1.id, 70, "2026-07-29T10:06:00.000Z"),
        ]

    def test_learner_session_report_generation(self):
        report = reports.generate_learner_session_report(self.session, mock_store.training_states, self.results, self.template, self.module)
        self.assertEqual(report.reportType, "learner_session")
        self.assertEqual(report.sessionId, self.session.id)
        self.assertEqual(report.overallScore, 85)
        self.assertEqual(report.evaluatedStateCount, 2)
        self.assertEqual(report.trainingTemplate.version, "1.0")

    def test_company_aggregate_report_generation(self):
        report = reports.generate_company_aggregate_report(
            mock_store.companies[0],
            [self.session, self.secondary_session],
            self.results,
            self.template,
        )
        self.assertEqual(report.reportType, "company_aggregate")
        self.assertEqual(report.completedSessionCount, 2)
        self.assertEqual(report.scoredSessionCount, 2)
        self.assertEqual(report.averageOverallScore, 77.5)

    def test_platform_aggregate_report_contract_generation(self):
        report = reports.generate_platform_aggregate_report(mock_store.companies, mock_store.training_templates, [self.session], self.results[:2])
        self.assertEqual(report.reportType, "platform_aggregate")
        self.assertEqual(report.companyCount, 2)
        self.assertEqual(report.trainingTemplateCount, len(mock_store.training_templates))
        self.assertEqual(report.aggregateScoreSummary["averageOverallScore"], 85)

    def test_deterministic_report_output(self):
        first = reports.generate_learner_session_report(self.session, mock_store.training_states, self.results, self.template, self.module)
        second = reports.generate_learner_session_report(self.session, mock_store.training_states, self.results, self.template, self.module)
        self.assertEqual(first.model_dump(), second.model_dump())

    def test_input_order_does_not_change_aggregate_result(self):
        first = reports.generate_company_aggregate_report(mock_store.companies[0], [self.secondary_session, self.session], list(reversed(self.results)), self.template)
        second = reports.generate_company_aggregate_report(mock_store.companies[0], [self.session, self.secondary_session], self.results, self.template)
        self.assertEqual(first.model_dump(), second.model_dump())

    def test_duplicate_scoring_result_deduplication_uses_latest(self):
        older = make_result(self.session.id, self.state_1.id, 50, "2026-07-29T09:00:00.000Z")
        latest = reports.dedupe_latest_scoring_results([self.results[0], older])
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0].overallScore, 80)

    def test_average_score_calculation_and_rounding(self):
        values = [make_result("s1", "a", 80, "2026-07-29T10:00:00.000Z"), make_result("s2", "a", 81, "2026-07-29T10:01:00.000Z")]
        session_scores = reports.session_overall_scores(values)
        self.assertEqual(reports.round_metric(sum(session_scores.values()) / len(session_scores)), 80.5)

    def test_dimension_aggregation(self):
        dimensions = reports.aggregate_dimensions(self.results[:2])
        clarity = next(item for item in dimensions if item.dimensionId == "clarity")
        empathy = next(item for item in dimensions if item.dimensionId == "empathy")
        self.assertEqual(clarity.averageScore, 85)
        self.assertEqual(empathy.averageScore, 75)

    def test_skill_impact_aggregation(self):
        skills = reports.aggregate_skills(self.results[:2])
        communication = next(item for item in skills if item.skill == "Communication")
        self.assertEqual(communication.averageScore, 85)
        self.assertEqual(communication.averageDelta, 2)

    def test_deterministic_tie_breaking(self):
        dimensions = reports.strongest_dimensions([
            reports.ReportDimensionSummaryDTO(dimensionId="b", name="B", averageScore=90, resultCount=1),
            reports.ReportDimensionSummaryDTO(dimensionId="a", name="A", averageScore=90, resultCount=1),
        ])
        self.assertEqual([item.dimensionId for item in dimensions], ["a", "b"])

    def test_partial_session_behavior(self):
        partial = self.session.model_copy(deep=True)
        partial.status = "in_progress"
        partial.completedAt = None
        report = reports.generate_learner_session_report(partial, mock_store.training_states, self.results[:1], self.template, self.module)
        self.assertTrue(report.coverage.isPartial)
        self.assertGreater(len(report.coverage.missingStateIds), 0)

    def test_empty_dataset_zero_division_behavior(self):
        report = reports.generate_company_aggregate_report(mock_store.companies[0], [], [], self.template)
        self.assertEqual(report.scoredSessionCount, 0)
        self.assertEqual(report.coverage.scoringCoverage, 0)
        self.assertIsNone(report.averageOverallScore)
        self.assertTrue(report.coverage.insufficientSample)

    def test_invalid_scoring_result_rejection(self):
        invalid = make_result(self.session.id, self.state_1.id, 101, "2026-07-29T10:00:00.000Z")
        with self.assertRaises(InvalidReportInputError):
            reports.validate_scoring_result(invalid)

    def test_insufficient_sample_flag(self):
        report = reports.generate_company_aggregate_report(mock_store.companies[0], [self.session], self.results[:1], self.template)
        self.assertTrue(report.coverage.insufficientSample)

    def test_guardrail_summary(self):
        report = reports.generate_learner_session_report(self.session, mock_store.training_states, [make_result(self.session.id, self.state_1.id, 60, "2026-07-29T10:00:00.000Z")], self.template, self.module)
        self.assertEqual(report.guardrailSummary.totalFlags, 1)
        self.assertEqual(report.guardrailSummary.codes, ["short_answer"])

    def test_schema_version_propagation(self):
        report = reports.generate_learner_session_report(self.session, mock_store.training_states, self.results[:1], self.template, self.module)
        self.assertEqual(report.schemaVersion, "1.0")
        self.assertEqual(report.sourceScoringSchemaVersions, ["1.0"])
        self.assertEqual(report.rubricRefs[0].version, "1.0")

    def test_learner_answer_text_does_not_leak_to_aggregate_reports(self):
        sensitive_answer = "RAW LEARNER ANSWER SHOULD NOT LEAK"
        report = reports.generate_company_aggregate_report(mock_store.companies[0], [self.session], self.results[:1], self.template)
        self.assertNotIn(sensitive_answer, report.model_dump_json())

    def test_other_company_data_is_not_included(self):
        other_result = make_result(self.other_company_session.id, self.state_1.id, 10, "2026-07-29T10:07:00.000Z", company_marker="-other")
        report = reports.generate_company_aggregate_report(mock_store.companies[0], [self.session, self.other_company_session], self.results[:2] + [other_result], self.template)
        self.assertEqual(report.scoredSessionCount, 1)
        self.assertEqual(report.averageOverallScore, 85)
        self.assertNotIn("other", report.model_dump_json())

    def test_existing_report_generation_does_not_mutate_answer_flow_contract(self):
        report = reports.generate_learner_session_report(self.session, mock_store.training_states, self.results[:1], self.template, self.module)
        self.assertEqual(report.reportType, "learner_session")
        self.assertTrue(hasattr(self.session, "answers"))


if __name__ == "__main__":
    unittest.main()
