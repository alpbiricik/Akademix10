import hashlib
import json
import os
import threading
import uuid
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field

from app.core.auth import Principal
from app.db.supabase_mappers import session_from_row, state_from_row, usage_from_row
from app.db.supabase_rest import SupabaseRequestError, SupabaseUserClient
from app.schemas.dtos import StructuredScoringResultDTO, TrainingSessionDTO, TrainingStateDTO
from app.services import rubric_repository, scoring_service, session_engine
from app.services.finalization_cache import finalization_cache
from app.services.conversation_cache import conversation_cache
from app.services.scoring_result_reader import read_scoring_results

FINALIZE_CONTRACT_VERSION = "2.0"
DEFAULT_MAX_FINALIZE_ANSWERS = 64
DEFAULT_MAX_FINALIZE_ANSWER_CHARS = 8000


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


class MissingSessionAnswersError(FinalizationValidationError):
    code = "missing_session_answers"

    def __init__(self, state_ids: list[str]):
        super().__init__("Required answers are unavailable. Answer these steps again.")
        self.missing_state_ids = sorted(state_ids)


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
    if len(body.answers) > max_answers:
        raise FinalizationValidationError("Invalid answer count.")
    seen = set()
    state_ids = {state.id for state in states if state.completionRule == "answered"}
    for answer in body.answers:
        if answer.stateId in seen:
            raise FinalizationValidationError("Duplicate answer state.")
        seen.add(answer.stateId)
        if answer.stateId not in {state.id for state in states}:
            raise FinalizationValidationError("Answer state is not part of the session training.")
        if len(answer.answerText.strip()) < 2:
            raise FinalizationValidationError("Answer cannot be empty.")
        if len(answer.answerText) > max_chars:
            raise FinalizationValidationError("Answer exceeds finalization length limit.")
    missing = state_ids - seen
    if missing:
        raise MissingSessionAnswersError(list(missing))
    if not body.answers:
        raise FinalizationValidationError("Invalid answer count.")


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


def _with_live_answers(session_id: str, body: FinalizeRequestDTO, states: list[TrainingStateDTO]) -> FinalizeRequestDTO:
    answers = list(body.answers)
    supplied = {answer.stateId for answer in answers}
    for state in states:
        if state.id in supplied or not (state.avatarEnabled or state.type in {"avatar", "live_avatar", "roleplay"}):
            continue
        context = conversation_cache.get(f"conversation:{session_id}:{state.id}") or {}
        turns = [str(turn.get("learnerText", "")).strip() for turn in context.get("turns", [])]
        turns = [turn for turn in turns if turn]
        if turns:
            # The conversation contract bounds turns to 3 x 2000 characters.
            # Preserve every accepted learner answer; never score avatar words.
            text = "\n".join(turns)
            answers.append(FinalizeAnswerDTO(stateId=state.id, answerText=text))
    return body.model_copy(update={"answers": answers})


def _completed_response(client: SupabaseUserClient, session: TrainingSessionDTO, evaluation: dict) -> FinalizeResponseDTO:
    rows = client.select("reports", f"select=*&session_id=eq.{session.id}&limit=1")
    if not rows:
        raise FinalizationError("Completed evaluation report is unavailable.")
    row = rows[0]
    report = {
        "overallScore": row.get("overall_score", 0),
        "skillSummary": row.get("skill_summary") or [],
        "strengths": row.get("strengths") or [],
        "improvementAreas": row.get("improvement_areas") or [],
        "actionPlan": row.get("action_plan") or [],
    }
    conversation_cache.delete_prefix(f"conversation:{session.id}:")
    return FinalizeResponseDTO(status="completed", evaluationId=evaluation["id"], session=session,
                               scoringResults=read_scoring_results(client, session.id), report=report)


def finalize_session(session_id: str, body: FinalizeRequestDTO, principal: Principal) -> FinalizeResponseDTO:
    if not principal.access_token:
        raise FinalizationValidationError("Missing user access token.")
    client = SupabaseUserClient(principal.access_token)
    session = _load_session(client, session_id)
    if session.userId != principal.user_id or session.companyId != principal.company_id:
        raise FinalizationValidationError("Session not found.")
    # One claim per SESSION prevents different keys starting concurrent scoring.
    cache_key = f"finalization:{session_id}"
    fingerprint = _fingerprint(body)
    jobs = client.select("session_evaluations", f"select=id,status,payload_fingerprint,idempotency_key&session_id=eq.{session_id}")
    for job in jobs:
        if job.get("idempotency_key", body.idempotencyKey) == body.idempotencyKey:
            if job.get("payload_fingerprint") != fingerprint:
                raise FinalizationConflictError("Idempotency key payload conflict.")
            if job.get("status") == "completed":
                return _completed_response(client, session, job)
        elif job.get("status") == "completed":
            raise FinalizationConflictError("Session evaluation is already completed.")
    cached = finalization_cache.get(cache_key)
    if cached and (cached.get("fingerprint") != fingerprint or cached.get("key") != body.idempotencyKey):
        raise FinalizationConflictError("Idempotency key payload conflict.")
    payload = cached or {"fingerprint": fingerprint, "key": body.idempotencyKey, "results": []}
    owner = str(uuid.uuid4())
    payload["owner"] = owner
    ttl = _ttl_seconds()
    if not finalization_cache.claim(cache_key, payload, ttl):
        return FinalizeResponseDTO(status="processing", session=session, scoringResults=[], report={})
    stop_heartbeat = threading.Event()
    def renew():
        while not stop_heartbeat.wait(max(0.1, ttl / 3)):
            if not finalization_cache.renew_claim(cache_key, owner, ttl):
                return
    heartbeat = threading.Thread(target=renew, daemon=True, name="finalization-lease")
    heartbeat.start()
    try:
        # A preceding request may have committed between the first read and
        # acquiring the local claim. Recheck before any provider invocation.
        latest_jobs = client.select("session_evaluations", f"select=id,status,payload_fingerprint,idempotency_key&session_id=eq.{session_id}")
        for job in latest_jobs:
            if job.get("status") != "completed":
                continue
            if job.get("idempotency_key", body.idempotencyKey) != body.idempotencyKey or job.get("payload_fingerprint") != fingerprint:
                raise FinalizationConflictError("Session evaluation is already completed.")
            response = _completed_response(client, _load_session(client, session_id), job)
            finalization_cache.release_claim(cache_key, owner, delete=True)
            return response
        states = _load_states(client, session.moduleId)
        effective = _with_live_answers(session_id, body, states)
        _validate_answers(effective, states)
        by_state = {answer.stateId: answer.answerText for answer in effective.answers}
        evidence_fingerprint = _fingerprint(effective)
        if payload.get("evidenceFingerprint") not in {None, evidence_fingerprint}:
            raise FinalizationConflictError("Evaluation evidence changed during retry.")
        payload["evidenceFingerprint"] = evidence_fingerprint
        results = []
        saved_results = {item["stateId"]: StructuredScoringResultDTO.model_validate(item) for item in payload["results"]}
        working_session = session.model_copy(deep=True)
        for state in states:
            if state.id not in by_state:
                continue
            rubric = rubric_repository.get_rubric_for_state(working_session.templateId, state.id, state.skillTags)
            result = saved_results.get(state.id) or scoring_service.score_answer(
                working_session,
                state,
                by_state[state.id],
                rubric,
                enforce_query_limit=False,
                max_answer_chars=DEFAULT_MAX_FINALIZE_ANSWER_CHARS,
            )
            working_session = session_engine.apply_scoring_result(working_session, result)
            results.append(result)
            # Keep only structured results for a bounded retry. If persistence
            # fails, a retry doesn't bill the provider again for finished states.
            payload["results"] = [item.model_dump() for item in results]
            finalization_cache.update_claim(cache_key, payload)
        report = _report_payload(results)
        if not finalization_cache.renew_claim(cache_key, owner, ttl):
            raise FinalizationConflictError("Finalization lease expired. Retry the request.")
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
        if not isinstance(rpc_result, dict) or rpc_result.get("status") != "completed":
            raise FinalizationError("Final evaluation persistence is not confirmed.")
        updated_session = _load_session(client, session_id)
        conversation_cache.delete_prefix(f"conversation:{session_id}:")
        finalization_cache.release_claim(cache_key, owner, delete=True)
        from app.services.voice_usage_service import schedule_voice_usage
        schedule_voice_usage(client, session_id)
        return FinalizeResponseDTO(
            status=(rpc_result or {}).get("status", "completed") if isinstance(rpc_result, dict) else "completed",
            evaluationId=(rpc_result or {}).get("evaluationId") if isinstance(rpc_result, dict) else None,
            session=updated_session,
            scoringResults=results,
            report=report,
        )
    except MissingSessionAnswersError:
        # No scoring started on this attempt. Allow users to restore missing
        # evidence immediately when there is no prior paid retry snapshot.
        finalization_cache.release_claim(cache_key, owner, delete=not bool(payload.get("results")))
        raise
    except SupabaseRequestError as error:
        finalization_cache.release_claim(cache_key, owner)
        if "payload conflict" in str(error).lower():
            raise FinalizationConflictError("Idempotency key payload conflict.") from error
        raise FinalizationError("Finalization could not be persisted.") from error
    except (FinalizationValidationError, FinalizationConflictError):
        finalization_cache.release_claim(cache_key, owner, delete=True)
        raise
    except Exception as error:
        finalization_cache.release_claim(cache_key, owner)
        raise FinalizationError("Final evaluation failed. Retry without changing answers.") from error
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=1)
