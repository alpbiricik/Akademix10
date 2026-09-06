import hashlib
import json
import os
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field

from app.core.auth import Principal
from app.db.supabase_mappers import session_from_row, state_from_row, usage_from_row
from app.db.supabase_rest import SupabaseRequestError, SupabaseUserClient
from app.schemas.dtos import StructuredScoringResultDTO, TrainingSessionDTO, TrainingStateDTO
from app.services import rubric_repository, scoring_service, session_engine
from app.services.finalization_cache import finalization_cache

FINALIZE_CONTRACT_VERSION = "2.0"
DEFAULT_MAX_FINALIZE_ANSWERS = 64
DEFAULT_MAX_FINALIZE_ANSWER_CHARS = 4000


class FinalizeAnswerDTO(BaseModel):
    stateId: str
    answerText: str


class FinalizeRequestDTO(BaseModel):
    idempotencyKey: str = Field(min_length=8, max_length=128)
    contractVersion: str = FINALIZE_CONTRACT_VERSION
    answers: list[FinalizeAnswerDTO]
    sessionVersion: str | None = None


class FinalizeResponseDTO(BaseModel):
    status: str
    evaluationId: str | None = None
    session: TrainingSessionDTO
    scoringResults: list[StructuredScoringResultDTO]
    report: dict[str, Any]


class FinalizationError(RuntimeError):
    code = "finalization_error"


class FinalizationConflictError(FinalizationError):
    code = "idempotency_conflict"


class FinalizationValidationError(FinalizationError):
    code = "invalid_finalization_payload"


def _ttl_seconds() -> int:
    raw = os.getenv("FINALIZATION_CACHE_TTL_SECONDS", "300")
    try:
        value = int(raw)
    except ValueError as error:
        raise FinalizationValidationError("Invalid finalization cache TTL configuration.") from error
    if value <= 0:
        raise FinalizationValidationError("Invalid finalization cache TTL configuration.")
    return value


def _fingerprint(body: FinalizeRequestDTO) -> str:
    normalized = {
        "contractVersion": body.contractVersion,
        "answers": sorted(
            [{"stateId": item.stateId, "answerText": item.answerText} for item in body.answers],
            key=lambda item: item["stateId"],
        ),
    }
    return hashlib.sha256(json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _load_session(client: SupabaseUserClient, session_id: str) -> TrainingSessionDTO:
    rows = client.select("training_sessions", f"select=*&id=eq.{session_id}&limit=1")
    if not rows:
        raise FinalizationValidationError("Session not found.")
    usage_rows = client.select("session_usage", f"select=*&session_id=eq.{session_id}&limit=1")
    return session_from_row(rows[0], usage_from_row(usage_rows[0] if usage_rows else None))


def _load_states(client: SupabaseUserClient, module_id: str) -> list[TrainingStateDTO]:
    return [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{module_id}&order=order_index.asc")]


def _validate_answers(body: FinalizeRequestDTO, states: list[TrainingStateDTO]) -> None:
    if body.contractVersion != FINALIZE_CONTRACT_VERSION:
        raise FinalizationValidationError("Unsupported finalization contract version.")
    max_answers = int(os.getenv("FINALIZATION_MAX_ANSWERS", str(DEFAULT_MAX_FINALIZE_ANSWERS)))
    max_chars = int(os.getenv("FINALIZATION_MAX_ANSWER_CHARS", str(DEFAULT_MAX_FINALIZE_ANSWER_CHARS)))
    if not body.answers or len(body.answers) > max_answers:
        raise FinalizationValidationError("Invalid answer count.")
    seen = set()
    state_ids = {state.id for state in states if state.completionRule == "answered"}
    for answer in body.answers:
        if answer.stateId in seen:
            raise FinalizationValidationError("Duplicate answer state.")
        seen.add(answer.stateId)
        if answer.stateId not in {state.id for state in states}:
            raise FinalizationValidationError("Answer state is not part of the session training.")
        if len(answer.answerText) > max_chars:
            raise FinalizationValidationError("Answer exceeds finalization length limit.")
    missing = state_ids - seen
    if missing:
        raise FinalizationValidationError("Required answer states are missing.")


def _report_payload(results: list[StructuredScoringResultDTO]) -> dict[str, Any]:
    scores = [result.overallScore for result in results]
    skill_summary: dict[str, dict[str, int]] = {}
    for result in results:
        for impact in result.skillImpacts:
            current = skill_summary.setdefault(impact.skill, {"score": 0, "delta": 0, "count": 0})
            current["score"] += impact.score or 0
            current["delta"] += impact.delta
            current["count"] += 1
    return {
        "overallScore": int(round(mean(scores))) if scores else 0,
        "skillSummary": [
            {"skill": skill, "score": int(round(values["score"] / values["count"])), "delta": int(round(values["delta"] / values["count"]))}
            for skill, values in sorted(skill_summary.items())
            if values["count"]
        ],
        "strengths": list(dict.fromkeys([item for result in results for item in result.strengths]))[:5],
        "improvementAreas": list(dict.fromkeys([item for result in results for item in result.improvementAreas]))[:5],
        "actionPlan": list(dict.fromkeys([result.recommendedNextAction for result in results]))[:5],
    }


def _usage_payload(results: list[StructuredScoringResultDTO], session: TrainingSessionDTO) -> dict[str, Any]:
    return {
        **session.usage.model_dump(),
        "inputTokens": sum(result.tokenCostMetadata.inputTokens for result in results),
        "outputTokens": sum(result.tokenCostMetadata.outputTokens for result in results),
        "estimatedCostUsd": sum(result.tokenCostMetadata.estimatedCostUsd for result in results),
    }


def finalize_session(session_id: str, body: FinalizeRequestDTO, principal: Principal) -> FinalizeResponseDTO:
    if not principal.access_token:
        raise FinalizationValidationError("Missing user access token.")
    cache_key = f"finalization:{session_id}:{body.idempotencyKey}"
    fingerprint = _fingerprint(body)
    cached = finalization_cache.get(cache_key)
    if cached and cached.get("fingerprint") != fingerprint:
        raise FinalizationConflictError("Idempotency key payload conflict.")
    if not finalization_cache.claim(cache_key, {"fingerprint": fingerprint}, _ttl_seconds()):
        session = _load_session(SupabaseUserClient(principal.access_token), session_id)
        return FinalizeResponseDTO(status="processing", session=session, scoringResults=[], report={})

    client = SupabaseUserClient(principal.access_token)
    try:
        session = _load_session(client, session_id)
        existing_jobs = client.select("session_evaluations", f"select=id,status,payload_fingerprint&session_id=eq.{session_id}&idempotency_key=eq.{body.idempotencyKey}&limit=1")
        if existing_jobs:
            existing = existing_jobs[0]
            if existing.get("payload_fingerprint") != fingerprint:
                raise FinalizationConflictError("Idempotency key payload conflict.")
        states = _load_states(client, session.moduleId)
        _validate_answers(body, states)
        by_state = {answer.stateId: answer.answerText for answer in body.answers}
        results = []
        working_session = session.model_copy(deep=True)
        for state in states:
            if state.id not in by_state:
                continue
            rubric = rubric_repository.get_rubric_for_state(working_session.templateId, state.id, state.skillTags)
            result = scoring_service.score_answer(
                working_session,
                state,
                by_state[state.id],
                rubric,
                enforce_query_limit=False,
            )
            working_session = session_engine.apply_scoring_result(working_session, result)
            results.append(result)
        report = _report_payload(results)
        rpc_result = client.rpc(
            "finalize_session_evaluation",
            {
                "p_session_id": session_id,
                "p_idempotency_key": body.idempotencyKey,
                "p_payload_fingerprint": fingerprint,
                "p_contract_version": body.contractVersion,
                "p_results": [result.model_dump() for result in results],
                "p_report": report,
                "p_usage": _usage_payload(results, session),
            },
        )
        finalization_cache.delete(cache_key)
        updated_session = _load_session(client, session_id)
        return FinalizeResponseDTO(
            status=(rpc_result or {}).get("status", "completed") if isinstance(rpc_result, dict) else "completed",
            evaluationId=(rpc_result or {}).get("evaluationId") if isinstance(rpc_result, dict) else None,
            session=updated_session,
            scoringResults=results,
            report=report,
        )
    except SupabaseRequestError as error:
        finalization_cache.release(cache_key)
        if "payload conflict" in str(error).lower():
            raise FinalizationConflictError("Idempotency key payload conflict.") from error
        raise FinalizationError("Finalization could not be persisted.") from error
    except Exception:
        finalization_cache.release(cache_key)
        raise
