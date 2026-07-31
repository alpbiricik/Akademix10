from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.dtos import (
    DimensionScoreDTO,
    GuardrailFlagDTO,
    ProviderRequestDTO,
    ProviderScoringResponseDTO,
    RubricDTO,
    SkillImpactDTO,
    StructuredScoringResultDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
)
from app.services.ai_provider import MAX_ANSWER_CHARS, MAX_PROVIDER_RETRIES, MAX_QUERIES_PER_STATE, MIN_ANSWER_CHARS, ScoringProvider
from app.services.mock_ai_provider import MockScoringProvider
from app.services.scoring_errors import AnswerGuardrailError, InvalidProviderOutputError, InvalidRubricError, MaxQueriesPerStateError, ProviderRetryExhaustedError
from app.services import scoring_repository


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_rubric(rubric: RubricDTO) -> None:
    if not rubric.dimensions:
        raise InvalidRubricError("Rubric must include at least one dimension.")
    total_weight = round(sum(dimension.weight for dimension in rubric.dimensions), 6)
    if total_weight != 1:
        raise InvalidRubricError(f"Rubric weights must sum to 1.0; got {total_weight}.")
    ids = set()
    for dimension in rubric.dimensions:
        if dimension.id in ids:
            raise InvalidRubricError(f"Duplicate rubric dimension id: {dimension.id}.")
        ids.add(dimension.id)
        if dimension.weight <= 0:
            raise InvalidRubricError(f"Dimension {dimension.id} weight must be positive.")
        if dimension.minScore >= dimension.maxScore:
            raise InvalidRubricError(f"Dimension {dimension.id} minScore must be lower than maxScore.")
        if not dimension.criteria:
            raise InvalidRubricError(f"Dimension {dimension.id} must include criteria.")
        if not dimension.skillTags:
            raise InvalidRubricError(f"Dimension {dimension.id} must map to at least one skill.")


def validate_answer(answer_text: str) -> list[GuardrailFlagDTO]:
    normalized = answer_text.strip()
    if len(normalized) < MIN_ANSWER_CHARS:
        raise AnswerGuardrailError("Answer is empty or too short to score.")
    if len(normalized) > MAX_ANSWER_CHARS:
        raise AnswerGuardrailError("Answer exceeds the scoring length limit.")
    flags = []
    if len(normalized.split()) < 3:
        flags.append(GuardrailFlagDTO(code="short_answer", message="Answer is very short; feedback may be limited.", severity="warning"))
    return flags


def validate_provider_output(rubric: RubricDTO, response: ProviderScoringResponseDTO) -> None:
    expected = {dimension.id: dimension for dimension in rubric.dimensions}
    returned = {score.dimensionId for score in response.dimensionScores}
    if returned != set(expected):
        raise InvalidProviderOutputError("Provider dimensions do not match rubric dimensions.")
    for score in response.dimensionScores:
        dimension = expected[score.dimensionId]
        if score.score < dimension.minScore or score.score > dimension.maxScore:
            raise InvalidProviderOutputError(f"Provider score for {score.dimensionId} is out of range.")


def call_provider_with_retry(provider: ScoringProvider, request: ProviderRequestDTO, rubric: RubricDTO) -> ProviderScoringResponseDTO:
    last_error: Exception | None = None
    for attempt in range(1, MAX_PROVIDER_RETRIES + 2):
        try:
            response = provider.score(request)
            if not isinstance(response, ProviderScoringResponseDTO):
                response = ProviderScoringResponseDTO.model_validate(response)
            response.providerMetadata.attemptCount = attempt
            validate_provider_output(rubric, response)
            return response
        except (ValidationError, InvalidProviderOutputError, ValueError, TypeError) as error:
            last_error = error
    raise ProviderRetryExhaustedError(f"Provider retry limit exhausted: {last_error}")


def calculate_overall_score(rubric: RubricDTO, dimension_scores: list[DimensionScoreDTO]) -> int:
    by_id = {score.dimensionId: score for score in dimension_scores}
    total = 0.0
    for dimension in rubric.dimensions:
        raw = by_id[dimension.id].score
        normalized = ((raw - dimension.minScore) / (dimension.maxScore - dimension.minScore)) * 100
        total += normalized * dimension.weight
    return int(round(total))


def calculate_skill_impacts(rubric: RubricDTO, dimension_scores: list[DimensionScoreDTO], session: TrainingSessionDTO) -> list[SkillImpactDTO]:
    by_id = {score.dimensionId: score for score in dimension_scores}
    impact_map: dict[str, dict[str, object]] = {}
    for dimension in rubric.dimensions:
        score = by_id[dimension.id].score
        delta = 1 if score < 70 else 2 if score < 85 else 3
        for skill in dimension.skillTags:
            entry = impact_map.setdefault(skill, {"deltas": [], "dimension_ids": []})
            entry["deltas"].append(delta)  # type: ignore[index,union-attr]
            entry["dimension_ids"].append(dimension.id)  # type: ignore[index,union-attr]

    current_scores = {item.skill: item.score for item in session.skillScores}
    impacts = []
    for skill in sorted(impact_map):
        deltas = impact_map[skill]["deltas"]  # type: ignore[index]
        dimension_ids = impact_map[skill]["dimension_ids"]  # type: ignore[index]
        delta = int(round(sum(deltas) / len(deltas)))  # type: ignore[arg-type]
        score = min(100, current_scores.get(skill, 70) + delta)
        impacts.append(SkillImpactDTO(skill=skill, delta=delta, score=score, sourceDimensionIds=list(dimension_ids)))  # type: ignore[arg-type]
    return impacts


def score_answer(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    answer_text: str,
    rubric: RubricDTO,
    provider: ScoringProvider | None = None,
) -> StructuredScoringResultDTO:
    validate_rubric(rubric)
    guardrail_flags = validate_answer(answer_text)
    if scoring_repository.get_query_count(session.id, state.id) >= MAX_QUERIES_PER_STATE:
        raise MaxQueriesPerStateError("Max queries per state exceeded.")
    scoring_repository.increment_query_count(session.id, state.id)

    active_provider = provider or MockScoringProvider()
    request = ProviderRequestDTO(
        sessionId=session.id,
        stateId=state.id,
        answerRef=f"{session.id}:{state.id}",
        answerText=answer_text,
        statePrompt=state.prompt,
        rubric=rubric,
        maxQueriesPerState=MAX_QUERIES_PER_STATE,
    )
    response = call_provider_with_retry(active_provider, request, rubric)

    result = StructuredScoringResultDTO(
        sessionId=session.id,
        stateId=state.id,
        answerRef=request.answerRef,
        rubricId=rubric.id,
        rubricVersion=rubric.version,
        overallScore=calculate_overall_score(rubric, response.dimensionScores),
        dimensionScores=response.dimensionScores,
        conciseLearnerFeedback=response.conciseLearnerFeedback,
        strengths=response.strengths,
        improvementAreas=response.improvementAreas,
        recommendedNextAction=response.recommendedNextAction,
        skillImpacts=calculate_skill_impacts(rubric, response.dimensionScores, session),
        guardrailFlags=guardrail_flags + response.guardrailFlags,
        providerMetadata=response.providerMetadata,
        tokenCostMetadata=response.tokenCostMetadata,
        generatedAt=now_iso(),
    )
    return scoring_repository.save_scoring_result(result)
