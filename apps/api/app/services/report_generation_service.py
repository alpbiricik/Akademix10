from collections import defaultdict
from statistics import mean

from app.schemas.dtos import (
    CompanyAggregateReportDTO,
    CompanyDTO,
    LearnerSessionReportDTO,
    PlatformAggregateReportDTO,
    ReportCoverageDTO,
    ReportDimensionSummaryDTO,
    ReportGuardrailSummaryDTO,
    ReportProviderCostSummaryDTO,
    ReportReferenceDTO,
    ReportSkillSummaryDTO,
    StructuredScoringResultDTO,
    TrainingModuleDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    TrainingTemplateDTO,
)
from app.services.report_errors import InvalidReportInputError

REPORT_SCHEMA_VERSION = "1.0"
EMPTY_REPORT_TIMESTAMP = "1970-01-01T00:00:00+00:00"
INSUFFICIENT_SAMPLE_SESSION_THRESHOLD = 2
ROUND_DECIMALS = 2


def round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, ROUND_DECIMALS)


def validate_scoring_result(result: StructuredScoringResultDTO) -> None:
    if not result.schemaVersion or not result.sessionId or not result.stateId:
        raise InvalidReportInputError("Scoring result is missing required identity fields.")
    if not result.rubricId or not result.rubricVersion:
        raise InvalidReportInputError("Scoring result is missing rubric reference.")
    if result.overallScore < 0 or result.overallScore > 100:
        raise InvalidReportInputError("Scoring result overallScore is out of range.")
    if not result.dimensionScores:
        raise InvalidReportInputError("Scoring result must include dimension scores.")
    dimension_ids = set()
    for dimension in result.dimensionScores:
        if dimension.dimensionId in dimension_ids:
            raise InvalidReportInputError("Scoring result has duplicate dimension scores.")
        dimension_ids.add(dimension.dimensionId)
        if dimension.score < 0 or dimension.score > 100:
            raise InvalidReportInputError("Scoring result dimension score is out of range.")


def dedupe_latest_scoring_results(results: list[StructuredScoringResultDTO]) -> list[StructuredScoringResultDTO]:
    latest: dict[tuple[str, str], StructuredScoringResultDTO] = {}
    for result in results:
        validate_scoring_result(result)
        key = (result.sessionId, result.stateId)
        current = latest.get(key)
        if current is None or (result.generatedAt, result.answerRef) > (current.generatedAt, current.answerRef):
            latest[key] = result
    return sorted(latest.values(), key=lambda item: (item.sessionId, item.stateId, item.generatedAt, item.answerRef))


def deterministic_generated_at(results: list[StructuredScoringResultDTO], fallback: str = EMPTY_REPORT_TIMESTAMP) -> str:
    if not results:
        return fallback
    return max(result.generatedAt for result in results)


def unique_ordered(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def source_schema_versions(results: list[StructuredScoringResultDTO]) -> list[str]:
    return sorted({result.schemaVersion for result in results})


def aggregate_dimensions(results: list[StructuredScoringResultDTO]) -> list[ReportDimensionSummaryDTO]:
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    names: dict[str, str] = {}
    for result in results:
        for dimension in result.dimensionScores:
            grouped[dimension.dimensionId].append((result.stateId, dimension.score))
            names[dimension.dimensionId] = dimension.name
    summaries = [
        ReportDimensionSummaryDTO(
            dimensionId=dimension_id,
            name=names[dimension_id],
            averageScore=round_metric(mean(score for _, score in values)) or 0,
            resultCount=len(values),
        )
        for dimension_id, values in grouped.items()
    ]
    return sorted(summaries, key=lambda item: item.dimensionId)


def aggregate_skills(results: list[StructuredScoringResultDTO]) -> list[ReportSkillSummaryDTO]:
    grouped: dict[str, list[tuple[int | None, int]]] = defaultdict(list)
    for result in results:
        for impact in result.skillImpacts:
            grouped[impact.skill].append((impact.score, impact.delta))
    summaries = []
    for skill, values in grouped.items():
        scores = [score for score, _ in values if score is not None]
        summaries.append(
            ReportSkillSummaryDTO(
                skill=skill,
                averageScore=round_metric(mean(scores)) if scores else None,
                averageDelta=round_metric(mean(delta for _, delta in values)) or 0,
                resultCount=len(values),
            )
        )
    return sorted(summaries, key=lambda item: item.skill)


def guardrail_summary(results: list[StructuredScoringResultDTO]) -> ReportGuardrailSummaryDTO:
    by_severity: dict[str, int] = {}
    codes = []
    for result in results:
        for flag in result.guardrailFlags:
            by_severity[flag.severity] = by_severity.get(flag.severity, 0) + 1
            codes.append(flag.code)
    return ReportGuardrailSummaryDTO(totalFlags=len(codes), bySeverity=dict(sorted(by_severity.items())), codes=sorted(set(codes)))


def provider_cost_summary(results: list[StructuredScoringResultDTO]) -> ReportProviderCostSummaryDTO:
    currencies = sorted({result.tokenCostMetadata.currency for result in results}) if results else ["USD"]
    return ReportProviderCostSummaryDTO(
        providers=sorted({result.providerMetadata.provider for result in results}),
        models=sorted({result.providerMetadata.model for result in results}),
        inputTokens=sum(result.tokenCostMetadata.inputTokens for result in results),
        outputTokens=sum(result.tokenCostMetadata.outputTokens for result in results),
        estimatedCostUsd=round_metric(sum(result.tokenCostMetadata.estimatedCostUsd for result in results)) or 0,
        currency=currencies[0],
    )


def strongest_dimensions(dimensions: list[ReportDimensionSummaryDTO], limit: int = 3) -> list[ReportDimensionSummaryDTO]:
    return sorted(dimensions, key=lambda item: (-item.averageScore, item.dimensionId))[:limit]


def priority_dimensions(dimensions: list[ReportDimensionSummaryDTO], limit: int = 3) -> list[ReportDimensionSummaryDTO]:
    return sorted(dimensions, key=lambda item: (item.averageScore, item.dimensionId))[:limit]


def strongest_skills(skills: list[ReportSkillSummaryDTO], limit: int = 3) -> list[ReportSkillSummaryDTO]:
    return sorted(skills, key=lambda item: (-(item.averageScore if item.averageScore is not None else -1), item.skill))[:limit]


def priority_skills(skills: list[ReportSkillSummaryDTO], limit: int = 3) -> list[ReportSkillSummaryDTO]:
    return sorted(skills, key=lambda item: ((item.averageScore if item.averageScore is not None else 101), item.skill))[:limit]


def session_overall_scores(results: list[StructuredScoringResultDTO]) -> dict[str, float]:
    by_session: dict[str, list[int]] = defaultdict(list)
    for result in results:
        by_session[result.sessionId].append(result.overallScore)
    return {session_id: round_metric(mean(scores)) or 0 for session_id, scores in by_session.items()}


def generate_learner_session_report(
    session: TrainingSessionDTO,
    states: list[TrainingStateDTO],
    scoring_results: list[StructuredScoringResultDTO],
    template: TrainingTemplateDTO,
    module: TrainingModuleDTO,
) -> LearnerSessionReportDTO:
    session_results = dedupe_latest_scoring_results([result for result in scoring_results if result.sessionId == session.id])
    ordered_state_ids = [state.id for state in sorted(states, key=lambda item: item.order)]
    scored_state_ids = {result.stateId for result in session_results}
    dimension_summaries = aggregate_dimensions(session_results)
    skill_summaries = aggregate_skills(session_results)
    overall = round_metric(mean(result.overallScore for result in session_results)) if session_results else None
    missing_state_ids = [state_id for state_id in ordered_state_ids if state_id not in scored_state_ids]
    coverage = ReportCoverageDTO(
        expectedStateCount=len(ordered_state_ids),
        evaluatedStateCount=len(session_results),
        scoredSessionCount=1 if session_results else 0,
        totalSessionCount=1,
        scoringCoverage=round_metric(len(session_results) / len(ordered_state_ids)) if ordered_state_ids else 0,
        completionRate=1 if session.status == "completed" else 0,
        isPartial=session.status != "completed" or bool(missing_state_ids),
        missingStateIds=missing_state_ids,
        insufficientSample=False,
    )
    generated_at = deterministic_generated_at(session_results, session.updatedAt)
    return LearnerSessionReportDTO(
        id=f"learner-report-{session.id}-{REPORT_SCHEMA_VERSION}",
        schemaVersion=REPORT_SCHEMA_VERSION,
        sourceScoringSchemaVersions=source_schema_versions(session_results),
        generatedAt=generated_at,
        sessionId=session.id,
        learner=ReportReferenceDTO(id=session.userId),
        company=ReportReferenceDTO(id=session.companyId),
        trainingTemplate=ReportReferenceDTO(id=template.id, label=template.title, version=template.version),
        trainingModule=ReportReferenceDTO(id=module.id, label=module.title),
        sessionStatus=session.status,
        completedAt=session.completedAt,
        evaluatedStateCount=len(session_results),
        overallScore=overall,
        dimensionSummaries=dimension_summaries,
        skillSummaries=skill_summaries,
        strengths=unique_ordered([strength for result in session_results for strength in result.strengths])[:5],
        improvementAreas=unique_ordered([area for result in session_results for area in result.improvementAreas])[:5],
        recommendedNextActions=unique_ordered([result.recommendedNextAction for result in session_results])[:5],
        guardrailSummary=guardrail_summary(session_results),
        coverage=coverage,
        rubricRefs=[
            ReportReferenceDTO(id=rubric_id, version=version)
            for rubric_id, version in sorted({(result.rubricId, result.rubricVersion) for result in session_results})
        ],
        providerCostSummary=provider_cost_summary(session_results),
    )


def generate_company_aggregate_report(
    company: CompanyDTO,
    sessions: list[TrainingSessionDTO],
    scoring_results: list[StructuredScoringResultDTO],
    template: TrainingTemplateDTO | None = None,
    filter_summary: dict[str, object] | None = None,
) -> CompanyAggregateReportDTO:
    company_sessions = sorted([session for session in sessions if session.companyId == company.id], key=lambda item: item.id)
    session_ids = {session.id for session in company_sessions}
    results = dedupe_latest_scoring_results([result for result in scoring_results if result.sessionId in session_ids])
    completed_count = sum(1 for session in company_sessions if session.status == "completed")
    scored_session_scores = session_overall_scores(results)
    dimension_summaries = aggregate_dimensions(results)
    skill_summaries = aggregate_skills(results)
    average_overall = round_metric(mean(scored_session_scores.values())) if scored_session_scores else None
    total_sessions = len(company_sessions)
    coverage = ReportCoverageDTO(
        evaluatedStateCount=len(results),
        scoredSessionCount=len(scored_session_scores),
        totalSessionCount=total_sessions,
        scoringCoverage=round_metric(len(scored_session_scores) / total_sessions) if total_sessions else 0,
        completionRate=round_metric(completed_count / total_sessions) if total_sessions else 0,
        isPartial=len(scored_session_scores) < total_sessions,
        insufficientSample=len(scored_session_scores) < INSUFFICIENT_SAMPLE_SESSION_THRESHOLD,
    )
    return CompanyAggregateReportDTO(
        id=f"company-report-{company.id}-{REPORT_SCHEMA_VERSION}",
        schemaVersion=REPORT_SCHEMA_VERSION,
        sourceScoringSchemaVersions=source_schema_versions(results),
        generatedAt=deterministic_generated_at(results),
        company=ReportReferenceDTO(id=company.id, label=company.name),
        trainingTemplate=ReportReferenceDTO(id=template.id, label=template.title, version=template.version) if template else None,
        filterSummary=filter_summary or {},
        totalAssignedLearnerCount=company.learnerCount,
        completedSessionCount=completed_count,
        scoredSessionCount=len(scored_session_scores),
        averageOverallScore=average_overall,
        dimensionAverages=dimension_summaries,
        skillAverages=skill_summaries,
        strongestDimensions=strongest_dimensions(dimension_summaries),
        developmentPriorityDimensions=priority_dimensions(dimension_summaries),
        strongestSkills=strongest_skills(skill_summaries),
        developmentPrioritySkills=priority_skills(skill_summaries),
        guardrailSummary=guardrail_summary(results),
        coverage=coverage,
        providerCostSummary=provider_cost_summary(results),
    )


def generate_platform_aggregate_report(
    companies: list[CompanyDTO],
    templates: list[TrainingTemplateDTO],
    sessions: list[TrainingSessionDTO],
    scoring_results: list[StructuredScoringResultDTO],
) -> PlatformAggregateReportDTO:
    results = dedupe_latest_scoring_results(scoring_results)
    scored_session_scores = session_overall_scores(results)
    completed_count = sum(1 for session in sessions if session.status == "completed")
    total_sessions = len(sessions)
    dimension_summaries = aggregate_dimensions(results)
    skill_summaries = aggregate_skills(results)
    coverage = ReportCoverageDTO(
        evaluatedStateCount=len(results),
        scoredSessionCount=len(scored_session_scores),
        totalSessionCount=total_sessions,
        scoringCoverage=round_metric(len(scored_session_scores) / total_sessions) if total_sessions else 0,
        completionRate=round_metric(completed_count / total_sessions) if total_sessions else 0,
        isPartial=len(scored_session_scores) < total_sessions,
        insufficientSample=len(scored_session_scores) < INSUFFICIENT_SAMPLE_SESSION_THRESHOLD,
    )
    average_overall = round_metric(mean(scored_session_scores.values())) if scored_session_scores else None
    return PlatformAggregateReportDTO(
        id=f"platform-report-{REPORT_SCHEMA_VERSION}",
        schemaVersion=REPORT_SCHEMA_VERSION,
        sourceScoringSchemaVersions=source_schema_versions(results),
        generatedAt=deterministic_generated_at(results),
        companyCount=len(companies),
        trainingTemplateCount=len(templates),
        sessionSummary=coverage,
        aggregateScoreSummary={
            "completedSessionCount": completed_count,
            "scoredSessionCount": len(scored_session_scores),
            "averageOverallScore": average_overall,
        },
        dimensionTrends=dimension_summaries,
        skillTrends=skill_summaries,
        reportCoverage=coverage,
        providerCostSummary=provider_cost_summary(results),
    )
