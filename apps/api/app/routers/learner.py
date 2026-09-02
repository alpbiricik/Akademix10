from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.auth import Principal, require_role, to_mock_principal
from app.core.auth import get_current_principal
from app.core.config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_STT_ENDPOINTING_MS,
    DEEPGRAM_STT_LANGUAGE,
    DEEPGRAM_STT_MODEL,
    ELEVENLABS_API_KEY,
    ELEVENLABS_STT_COMMIT_STRATEGY,
    ELEVENLABS_STT_LANGUAGE,
    ELEVENLABS_STT_MODEL,
    ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS,
    STT_PROVIDER,
)
from app.db.database import DatabaseMode, get_database_mode
from app.db.supabase_mappers import enrollment_from_row, module_from_row, session_from_row, state_from_row, template_from_row, usage_from_row
from app.db.supabase_rest import SupabaseRequestError, SupabaseUserClient
from app.schemas.dtos import (
    ConversationTurnRequestDTO,
    ConversationTurnResponseDTO,
    DimensionScoreDTO,
    EnrollmentDTO,
    GuardrailFlagDTO,
    LearnerSessionDataDTO,
    LearnerSessionReportDTO,
    ProviderMetadataDTO,
    ReportDTO,
    SkillImpactDTO,
    StructuredScoringResultDTO,
    TokenCostMetadataDTO,
    AvatarPolicyDTO,
    TrainingSessionDTO,
    TrainingTemplateDTO,
    VoiceOpeningResultDTO,
)
from app.services import mock_store
from app.services import conversation_service
from app.services.conversation_errors import ConversationError, ConversationProviderConfigurationError, ConversationStateError
from app.services.finalization_service import (
    FinalizationConflictError,
    FinalizationError,
    FinalizationValidationError,
    FinalizeRequestDTO,
    FinalizeResponseDTO,
    finalize_session,
)
from app.services import report_endpoint_service
from app.services import rubric_repository
from app.services import scoring_repository
from app.services import scoring_service
from app.services import session_engine
from app.services.deepgram_stt_provider import DeepgramSTTConfigurationError, DeepgramStreamingSpeechToTextProvider
from app.services.elevenlabs_stt_provider import ElevenLabsSTTConfigurationError, ElevenLabsSpeechToTextProvider
from app.services.mock_speech_to_text_provider import MockSpeechToTextProvider
from app.services.report_errors import ReportGenerationError
from app.services.scoring_errors import AnswerGuardrailError, InvalidProviderOutputError, InvalidRubricError, MaxQueriesPerStateError, ProviderRetryExhaustedError
from app.services.voice_turn_service import EmptyTranscriptError, VoiceTurnOrchestrator

router = APIRouter(prefix="/api/learner", tags=["learner"])


class StatePatchRequest(BaseModel):
    action: str = "complete"


class AnswerRequest(BaseModel):
    stateId: str
    answerText: str


def raise_report_http_error(error: ReportGenerationError) -> None:
    raise HTTPException(
        status_code=report_endpoint_service.to_http_status(error),
        detail={"code": error.code, "message": str(error)},
    )


def _client(principal: Principal) -> SupabaseUserClient:
    if not principal.access_token:
        raise HTTPException(status_code=401, detail="Missing user access token.")
    return SupabaseUserClient(principal.access_token)


def _load_session(client: SupabaseUserClient, session_id: str) -> TrainingSessionDTO:
    rows = client.select("training_sessions", f"select=*&id=eq.{session_id}&limit=1")
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found.")
    usage_rows = client.select("session_usage", f"select=*&session_id=eq.{session_id}&limit=1")
    return session_from_row(rows[0], usage_from_row(usage_rows[0] if usage_rows else None))


def _load_session_data(client: SupabaseUserClient, session_id: str) -> LearnerSessionDataDTO:
    session = _load_session(client, session_id)
    state_rows = client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")
    states = [state_from_row(row) for row in state_rows]
    module_rows = client.select("training_modules", f"select=*&id=eq.{session.moduleId}&limit=1")
    if not module_rows:
        raise HTTPException(status_code=404, detail="Training context not found.")
    module = module_from_row(module_rows[0], [state.id for state in states])
    template_rows = client.select("training_templates", f"select=*&id=eq.{session.templateId}&limit=1")
    template = template_from_row(template_rows[0]) if template_rows else _template_summary_from_module(session.templateId, module, states)
    return LearnerSessionDataDTO(
        session=session,
        states=states,
        module=module,
        template=template,
    )


def _template_summary_from_module(template_id: str, module, states) -> TrainingTemplateDTO:
    skill_tags = sorted({tag for state in states for tag in state.skillTags})
    avatar_budget_sec = sum(state.avatarBudgetSec for state in states if state.avatarEnabled)
    avatar_target_min = round(avatar_budget_sec / 60, 2) if avatar_budget_sec else 0
    return TrainingTemplateDTO(
        id=template_id,
        title=module.title,
        description=module.description,
        category="Assigned training",
        estimatedDurationMin=module.durationMin,
        defaultStateCount=len(states),
        skillTags=skill_tags,
        status=module.status,
        createdBy="",
        version="1.0",
        avatarPolicy=AvatarPolicyDTO(
            activeTargetMin=avatar_target_min,
            openCloseTarget=0,
            bufferedBillableMin=avatar_target_min,
            safeBudgetUsd=0,
        ),
    )


def _authorize_mock_session(session: TrainingSessionDTO, principal: Principal) -> None:
    if session.userId != principal.user_id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if principal.company_id and session.companyId != principal.company_id:
        raise HTTPException(status_code=403, detail="Session is outside the learner company boundary.")


def _stt_provider():
    if STT_PROVIDER == "elevenlabs":
        return ElevenLabsSpeechToTextProvider(
            api_key=ELEVENLABS_API_KEY,
            model=ELEVENLABS_STT_MODEL,
            language=ELEVENLABS_STT_LANGUAGE,
            commit_strategy=ELEVENLABS_STT_COMMIT_STRATEGY,
            vad_silence_threshold_secs=ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS,
        )
    if STT_PROVIDER == "deepgram":
        return DeepgramStreamingSpeechToTextProvider(
            api_key=DEEPGRAM_API_KEY,
            model=DEEPGRAM_STT_MODEL,
            language=DEEPGRAM_STT_LANGUAGE,
            endpointing_ms=DEEPGRAM_STT_ENDPOINTING_MS,
        )
    return MockSpeechToTextProvider(model="mock-stt-v1", language=ELEVENLABS_STT_LANGUAGE)


def _scoring_results_from_supabase(client: SupabaseUserClient, session_id: str) -> list[StructuredScoringResultDTO]:
    feedback_rows = client.select("session_feedback", f"select=*&session_id=eq.{session_id}&order=created_at.asc")
    if not feedback_rows:
        return []
    skill_rows = client.select("skill_scores", f"select=*&session_id=eq.{session_id}")
    skills_by_state: dict[str, list[SkillImpactDTO]] = {}
    for row in skill_rows:
        state_id = row.get("state_id")
        if not state_id:
            continue
        skills_by_state.setdefault(state_id, []).append(
            SkillImpactDTO(
                skill=row.get("skill", ""),
                score=row.get("score"),
                delta=row.get("delta", 0),
                sourceDimensionIds=[],
            )
        )

    results: list[StructuredScoringResultDTO] = []
    for row in feedback_rows:
        metadata = row.get("metadata") or {}
        dimensions = [
            DimensionScoreDTO(
                dimensionId=str(item.get("label", "")).lower().replace(" ", "_") or "dimension",
                name=item.get("label", ""),
                score=item.get("score", 0),
                rationale="",
            )
            for item in row.get("dimensions") or []
        ]
        guardrails = [
            GuardrailFlagDTO(
                code=item.get("code", ""),
                message=item.get("message", ""),
                severity=item.get("severity", "info"),
            )
            for item in metadata.get("guardrailFlags") or []
        ]
        results.append(
            StructuredScoringResultDTO(
                schemaVersion=metadata.get("schemaVersion", "1.0"),
                sessionId=session_id,
                stateId=row["state_id"],
                answerRef=f"{session_id}:{row['state_id']}:final",
                rubricId=metadata.get("rubricId", ""),
                rubricVersion=metadata.get("rubricVersion", ""),
                overallScore=row.get("overall_score", 0),
                dimensionScores=dimensions,
                conciseLearnerFeedback=row.get("feedback_text", ""),
                strengths=[],
                improvementAreas=[row.get("improvement_suggestion", "")] if row.get("improvement_suggestion") else [],
                recommendedNextAction=row.get("next_action") if row.get("next_action") in {"continue", "retry_state", "review_feedback", "complete_state"} else "complete_state",
                skillImpacts=skills_by_state.get(row["state_id"], []),
                guardrailFlags=guardrails,
                providerMetadata=ProviderMetadataDTO(
                    provider=row.get("provider") or "unknown",
                    model=row.get("model_name") or "unknown",
                ),
                tokenCostMetadata=TokenCostMetadataDTO(),
                generatedAt=row.get("created_at") or "",
            )
        )
    return results


@router.get("/trainings", response_model=list[EnrollmentDTO])
def get_learner_trainings(principal: Principal = Depends(require_role("learner"))) -> list[EnrollmentDTO]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        rows = client.select("learner_enrollments", f"select=*,company_training_assignments(template_id)&learner_id=eq.{principal.user_id}&order=assigned_at.desc")
        return [
            enrollment_from_row({**row, "template_id": (row.get("company_training_assignments") or {}).get("template_id")})
            for row in rows
        ]
    return mock_store.enrollments


@router.post("/sessions", response_model=TrainingSessionDTO)
def create_session(principal: Principal = Depends(require_role("learner"))) -> TrainingSessionDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        existing = client.select("training_sessions", f"select=*&learner_id=eq.{principal.user_id}&order=started_at.desc&limit=1")
        if existing:
            return _load_session(client, existing[0]["id"])
        enrollments = client.select("learner_enrollments", f"select=*&learner_id=eq.{principal.user_id}&status=in.(not_started,in_progress)&limit=1")
        if not enrollments:
            raise HTTPException(status_code=404, detail="Enrollment not found.")
        enrollment = enrollments[0]
        states = client.select("training_states", f"select=id&module_id=eq.{enrollment['module_id']}&order=order_index.asc&limit=1")
        if not states:
            raise HTTPException(status_code=404, detail="Training states not found.")
        created = client.insert(
            "training_sessions",
            {
                "enrollment_id": enrollment["id"],
                "module_id": enrollment["module_id"],
                "template_id": "00000000-0000-0000-0000-000000000404",
                "learner_id": principal.user_id,
                "company_id": enrollment["company_id"],
                "current_state_id": states[0]["id"],
                "status": "in_progress",
            },
        )
        if not created:
            raise HTTPException(status_code=502, detail="Session could not be created.")
        return _load_session(client, created[0]["id"])
    scoring_repository.reset_session_scoring_store("demo-session-1")
    mock_store.sessions["demo-session-1"] = mock_store.clone_session()
    return mock_store.sessions["demo-session-1"]


@router.get("/sessions/{session_id}", response_model=LearnerSessionDataDTO)
def get_session(session_id: str, principal: Principal = Depends(require_role("learner"))) -> LearnerSessionDataDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        return _load_session_data(_client(principal), session_id)
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _authorize_mock_session(session, principal)
    states = [state for state in mock_store.training_states if state.moduleId == session.moduleId]
    module = next((item for item in mock_store.training_modules if item.id == session.moduleId), None)
    template = next((item for item in mock_store.training_templates if item.id == session.templateId), None)
    if not module or not template:
        raise HTTPException(status_code=404, detail="Training context not found.")
    return LearnerSessionDataDTO(session=session, states=states, module=module, template=template)


@router.patch("/sessions/{session_id}/state", response_model=TrainingSessionDTO)
def patch_session_state(session_id: str, body: StatePatchRequest, principal: Principal = Depends(require_role("learner"))) -> TrainingSessionDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        session = _load_session(client, session_id)
        states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
        if body.action == "next":
            state = session_engine.get_next_state(session, states)
            payload = {"current_state_id": state.id} if state else {}
        elif body.action == "previous":
            state = session_engine.get_previous_state(session, states)
            payload = {"current_state_id": state.id} if state else {}
        else:
            completed = set(session.completedStateIds)
            completed.add(session.currentStateId)
            payload = {"completed_state_ids": list(completed), "status": "completed" if len(completed) >= len(states) else "in_progress"}
        if payload:
            client.patch("training_sessions", f"id=eq.{session_id}", payload)
        return _load_session(client, session_id)
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _authorize_mock_session(session, principal)
    if body.action == "next":
        next_state = session_engine.get_next_state(session, mock_store.training_states)
        if next_state:
            session.currentStateId = next_state.id
    elif body.action == "previous":
        previous_state = session_engine.get_previous_state(session, mock_store.training_states)
        if previous_state:
            session.currentStateId = previous_state.id
    else:
        session = session_engine.complete_current_state(session, mock_store.training_states)
    mock_store.sessions[session_id] = session
    return session


@router.post("/sessions/{session_id}/conversation-turn", response_model=ConversationTurnResponseDTO)
def post_conversation_turn(session_id: str, body: ConversationTurnRequestDTO, principal: Principal = Depends(require_role("learner"))) -> ConversationTurnResponseDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        session = _load_session(client, session_id)
        rows = client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")
        states = [state_from_row(row) for row in rows]
        state = next((item for item in states if item.id == body.stateId), None)
        if not state:
            raise HTTPException(status_code=404, detail="State not found.")
        try:
            result, turn_number, complete, guardrail = conversation_service.continue_training_conversation(session, state, body.learnerText)
        except ConversationProviderConfigurationError as error:
            raise HTTPException(status_code=503, detail={"code": error.code, "message": "Conversation provider is not configured."}) from error
        except ConversationStateError as error:
            raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
        except ConversationError as error:
            raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error
        if complete:
            completed = set(session.completedStateIds)
            completed.add(state.id)
            client.patch("training_sessions", f"id=eq.{session_id}", {"completed_state_ids": list(completed)})
            session = _load_session(client, session_id)
        return ConversationTurnResponseDTO(
            session=session,
            stateId=state.id,
            turnNumber=turn_number,
            assistantText=result.assistantText,
            action=result.action,
            conversationComplete=complete,
            guardrail=guardrail,
            providerMetadata=result.providerMetadata,
        )

    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _authorize_mock_session(session, principal)
    state = next((item for item in mock_store.training_states if item.id == body.stateId), None)
    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    try:
        result, turn_number, complete, guardrail = conversation_service.continue_training_conversation(session, state, body.learnerText)
    except ConversationProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": error.code, "message": "Conversation provider is not configured."}) from error
    except ConversationStateError as error:
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
    except ConversationError as error:
        raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error
    if complete and state.id not in session.completedStateIds:
        session.completedStateIds.append(state.id)
    mock_store.sessions[session_id] = session
    return ConversationTurnResponseDTO(
        session=session,
        stateId=state.id,
        turnNumber=turn_number,
        assistantText=result.assistantText,
        action=result.action,
        conversationComplete=complete,
        guardrail=guardrail,
        providerMetadata=result.providerMetadata,
    )


@router.post("/sessions/{session_id}/voice/opening", response_model=VoiceOpeningResultDTO)
def start_voice_opening(session_id: str, body: ConversationTurnRequestDTO, principal: Principal = Depends(require_role("learner"))) -> VoiceOpeningResultDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        session = _load_session(client, session_id)
        states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
    else:
        session = mock_store.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _authorize_mock_session(session, principal)
        states = mock_store.training_states
    state = next((item for item in states if item.id == body.stateId), None)
    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    try:
        return VoiceTurnOrchestrator(session, state).start_opening()
    except ConversationStateError as error:
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
    except ConversationProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": error.code, "message": "Conversation provider is not configured."}) from error
    except ConversationError as error:
        raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error


@router.websocket("/sessions/{session_id}/voice/stt")
async def stream_voice_turn(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        start = await websocket.receive_json()
        state_id = start.get("stateId")
        mock_role = start.get("mockRole")
        access_token = start.get("accessToken")
        if not isinstance(state_id, str):
            await websocket.send_json({"type": "error", "code": "missing_state_id"})
            await websocket.close(code=1008)
            return
        principal = get_current_principal(
            authorization=f"Bearer {access_token}" if isinstance(access_token, str) and access_token else None,
            x_mock_role=mock_role if isinstance(mock_role, str) else None,
        )
        if principal.role != "learner":
            await websocket.send_json({"type": "error", "code": "role_not_allowed"})
            await websocket.close(code=1008)
            return

        if get_database_mode() == DatabaseMode.SUPABASE:
            client = _client(principal)
            session = _load_session(client, session_id)
            states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
        else:
            session = mock_store.sessions.get(session_id)
            if not session:
                await websocket.send_json({"type": "error", "code": "session_not_found"})
                await websocket.close(code=1008)
                return
            _authorize_mock_session(session, principal)
            states = mock_store.training_states
        state = next((item for item in states if item.id == state_id), None)
        if not state:
            await websocket.send_json({"type": "error", "code": "state_not_found"})
            await websocket.close(code=1008)
            return

        orchestrator = VoiceTurnOrchestrator(session, state)
        orchestrator.ensure_accepting_turn()
        provider = _stt_provider()

        async def audio_chunks():
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"]:
                    yield message["bytes"]
                elif "text" in message and message["text"]:
                    if message["text"] in {"stop", "cancel"}:
                        break

        async for event in provider.stream(audio_chunks()):
            if event.type == "partial_transcript":
                orchestrator.handle_partial(event)
                await websocket.send_json({"type": event.type, "transcript": event.transcript, "metadata": event.metadata.model_dump()})
            elif event.type in {"final_transcript", "committed_transcript"}:
                await websocket.send_json({"type": event.type, "transcript": event.transcript, "metadata": event.metadata.model_dump()})
                try:
                    result = orchestrator.handle_final(event)
                except EmptyTranscriptError:
                    await websocket.send_json({"type": "error", "code": "empty_transcript"})
                    continue
                if result:
                    if result.conversationComplete:
                        if get_database_mode() == DatabaseMode.SUPABASE:
                            completed = set(session.completedStateIds)
                            completed.add(state.id)
                            client.patch("training_sessions", f"id=eq.{session_id}", {"completed_state_ids": list(completed)})
                        elif state.id not in session.completedStateIds:
                            session.completedStateIds.append(state.id)
                            mock_store.sessions[session_id] = session
                    await websocket.send_json({"type": "voice_turn_result", "result": result.model_dump()})
            else:
                await websocket.send_json({"type": event.type, "metadata": event.metadata.model_dump()})
        await websocket.close()
    except (DeepgramSTTConfigurationError, ElevenLabsSTTConfigurationError):
        await websocket.send_json({"type": "error", "code": "stt_provider_not_configured"})
        await websocket.close(code=1011)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.send_json({"type": "error", "code": "voice_stream_error"})
        await websocket.close(code=1011)


@router.post("/sessions/{session_id}/answers")
def post_answer(session_id: str, body: AnswerRequest, principal: Principal = Depends(require_role("learner"))) -> dict[str, object]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        session = _load_session(client, session_id)
        states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
        state = next((item for item in states if item.id == body.stateId), None)
        if not state:
            raise HTTPException(status_code=404, detail="State not found.")
        # Raw answer persistence is intentionally deferred to Phase 2B-E.
        session = session_engine.submit_answer(session, body.stateId, body.answerText)
        rubric = rubric_repository.get_rubric_for_state(session.templateId, state.id)
        try:
            scoring_result = scoring_service.score_answer(session, state, body.answerText, rubric)
        except MaxQueriesPerStateError as error:
            raise HTTPException(status_code=429, detail={"code": error.code, "message": str(error)}) from error
        except (AnswerGuardrailError, InvalidRubricError) as error:
            raise HTTPException(status_code=422, detail={"code": error.code, "message": str(error)}) from error
        except (InvalidProviderOutputError, ProviderRetryExhaustedError) as error:
            raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error
        session = session_engine.apply_scoring_result(session, scoring_result)
        feedback = session_engine.feedback_from_scoring_result(scoring_result)
        completed = set(session.completedStateIds)
        completed.add(body.stateId)
        try:
            client.patch("training_sessions", f"id=eq.{session_id}", {"completed_state_ids": list(completed), "current_state_id": session.currentStateId})
        except SupabaseRequestError as error:
            raise HTTPException(status_code=error.status_code, detail="Session progress could not be persisted.") from error
        return {"session": session.model_dump(), "feedback": feedback.model_dump(), "scoringResult": scoring_result.model_dump()}
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _authorize_mock_session(session, principal)
    state = next((item for item in mock_store.training_states if item.id == body.stateId), None)
    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    session = session_engine.submit_answer(session, body.stateId, body.answerText)
    rubric = rubric_repository.get_rubric_for_state(session.templateId, state.id)
    try:
        scoring_result = scoring_service.score_answer(session, state, body.answerText, rubric)
    except MaxQueriesPerStateError as error:
        raise HTTPException(status_code=429, detail={"code": error.code, "message": str(error)}) from error
    except (AnswerGuardrailError, InvalidRubricError) as error:
        raise HTTPException(status_code=422, detail={"code": error.code, "message": str(error)}) from error
    except (InvalidProviderOutputError, ProviderRetryExhaustedError) as error:
        raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error
    session = session_engine.apply_scoring_result(session, scoring_result)
    feedback = session_engine.feedback_from_scoring_result(scoring_result)
    mock_store.sessions[session_id] = session
    return {"session": session.model_dump(), "feedback": feedback.model_dump(), "scoringResult": scoring_result.model_dump()}


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeResponseDTO)
def finalize_learner_session(session_id: str, body: FinalizeRequestDTO, principal: Principal = Depends(require_role("learner"))) -> FinalizeResponseDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        try:
            return finalize_session(session_id, body, principal)
        except FinalizationConflictError as error:
            raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
        except FinalizationValidationError as error:
            raise HTTPException(status_code=422, detail={"code": error.code, "message": str(error)}) from error
        except FinalizationError as error:
            raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error

    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    results = []
    for answer in body.answers:
        state = next((item for item in mock_store.training_states if item.id == answer.stateId), None)
        if not state:
            raise HTTPException(status_code=422, detail={"code": "invalid_finalization_payload", "message": "Answer state is not part of the session training."})
        rubric = rubric_repository.get_rubric_for_state(session.templateId, state.id)
        result = scoring_service.score_answer(session, state, answer.answerText, rubric, enforce_query_limit=False)
        session = session_engine.apply_scoring_result(session, result)
        results.append(result)
    session.status = "completed"
    mock_store.sessions[session_id] = session
    return FinalizeResponseDTO(status="completed", evaluationId=f"mock-evaluation-{session_id}", session=session, scoringResults=results, report={})


@router.get("/sessions/{session_id}/scoring-results", response_model=list[StructuredScoringResultDTO])
def get_session_scoring_results(session_id: str, principal: Principal = Depends(require_role("learner"))) -> list[StructuredScoringResultDTO]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        _load_session(client, session_id)
        return _scoring_results_from_supabase(client, session_id)
    try:
        return report_endpoint_service.get_learner_scoring_results(session_id, to_mock_principal(principal))
    except ReportGenerationError as error:
        raise_report_http_error(error)


@router.get("/sessions/{session_id}/report", response_model=LearnerSessionReportDTO)
def get_session_structured_report(session_id: str, principal: Principal = Depends(require_role("learner"))) -> LearnerSessionReportDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        session = _load_session(client, session_id)
        reports = client.select("reports", f"select=*&session_id=eq.{session_id}&limit=1")
        if not reports:
            raise HTTPException(status_code=404, detail="Report not found.")
        report = reports[0]
        from app.schemas.dtos import (
            ReportCoverageDTO,
            ReportGuardrailSummaryDTO,
            ReportProviderCostSummaryDTO,
            ReportReferenceDTO,
            ReportSkillSummaryDTO,
        )

        skill_summaries = [
            ReportSkillSummaryDTO(skill=item.get("skill", ""), averageScore=item.get("score"), averageDelta=item.get("delta", 0), resultCount=1)
            for item in report.get("skill_summary") or []
        ]
        return LearnerSessionReportDTO(
            id=report["id"],
            sourceScoringSchemaVersions=["1.0"],
            generatedAt=report.get("generated_at") or "",
            sessionId=session_id,
            learner=ReportReferenceDTO(id=session.userId),
            company=ReportReferenceDTO(id=session.companyId),
            trainingTemplate=ReportReferenceDTO(id=session.templateId),
            trainingModule=ReportReferenceDTO(id=session.moduleId),
            sessionStatus=session.status,
            completedAt=session.completedAt,
            evaluatedStateCount=len(skill_summaries),
            overallScore=report.get("overall_score"),
            dimensionSummaries=[],
            skillSummaries=skill_summaries,
            strengths=report.get("strengths") or [],
            improvementAreas=report.get("improvement_areas") or [],
            recommendedNextActions=[],
            guardrailSummary=ReportGuardrailSummaryDTO(),
            coverage=ReportCoverageDTO(evaluatedStateCount=len(skill_summaries), scoredSessionCount=1, totalSessionCount=1, scoringCoverage=1),
            rubricRefs=[],
            providerCostSummary=ReportProviderCostSummaryDTO(),
        )
    try:
        return report_endpoint_service.get_learner_session_report(session_id, to_mock_principal(principal))
    except ReportGenerationError as error:
        raise_report_http_error(error)


@router.get("/sessions/{session_id}/scoring/{state_id}", response_model=StructuredScoringResultDTO)
def get_scoring_result(session_id: str, state_id: str, principal: Principal = Depends(require_role("learner"))) -> StructuredScoringResultDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        _load_session(client, session_id)
        result = next((item for item in _scoring_results_from_supabase(client, session_id) if item.stateId == state_id), None)
        if not result:
            raise HTTPException(status_code=404, detail="Scoring result not found.")
        return result
    try:
        report_endpoint_service.get_session_for_learner(session_id, to_mock_principal(principal))
    except ReportGenerationError as error:
        raise_report_http_error(error)
    result = scoring_repository.get_scoring_result(session_id, state_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scoring result not found.")
    return result


@router.get("/reports/{session_id}", response_model=ReportDTO)
def get_report(session_id: str, principal: Principal = Depends(require_role("learner"))) -> ReportDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        from app.db.supabase_mappers import report_from_row

        rows = client.select("reports", f"select=*&session_id=eq.{session_id}&limit=1")
        if not rows:
            raise HTTPException(status_code=404, detail="Report not found.")
        return report_from_row(rows[0])
    if session_id != mock_store.demo_report.sessionId:
        raise HTTPException(status_code=404, detail="Report not found.")
    return mock_store.demo_report
