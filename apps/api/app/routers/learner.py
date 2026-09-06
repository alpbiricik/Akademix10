from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.auth import Principal, require_role
from app.core.auth import get_current_principal
from app.core.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_STT_COMMIT_STRATEGY,
    ELEVENLABS_STT_LANGUAGE,
    ELEVENLABS_STT_MODEL,
    ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS,
    ELEVENLABS_TTS_LANGUAGE,
    ELEVENLABS_TTS_MODEL,
    ELEVENLABS_TTS_VOICE_ID,
    STT_PROVIDER,
    TTS_LANGUAGE,
    TTS_PROVIDER,
)
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
    TextToSpeechResultDTO,
    TokenCostMetadataDTO,
    AvatarPolicyDTO,
    LiveAvatarSessionActionRequestDTO,
    LiveAvatarSessionActionResponseDTO,
    LiveAvatarSessionTokenRequestDTO,
    LiveAvatarSessionTokenResponseDTO,
    TrainingModuleDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    TrainingTemplateDTO,
    VoiceOpeningResultDTO,
    VoiceTurnResultDTO,
)
from app.services import conversation_service
from app.services import live_avatar_service
from app.services.conversation_errors import ConversationError, ConversationProviderConfigurationError, ConversationStateError
from app.services.live_avatar_provider import LiveAvatarConfigurationError, LiveAvatarProviderError

from app.services.finalization_service import (
    FinalizationConflictError,
    FinalizationError,
    FinalizationValidationError,
    FinalizeRequestDTO,
    FinalizeResponseDTO,
    finalize_session,
)
from app.services import rubric_repository
from app.services import scoring_service
from app.services import session_engine
from app.services.elevenlabs_stt_provider import ElevenLabsSTTConfigurationError, ElevenLabsSpeechToTextProvider
from app.services.elevenlabs_tts_provider import ElevenLabsTextToSpeechProvider
from app.services.text_to_speech_provider import TextToSpeechError

from app.services.scoring_errors import AnswerGuardrailError, InvalidProviderOutputError, InvalidRubricError, MaxQueriesPerStateError, ProviderRetryExhaustedError
from app.services.voice_turn_service import EmptyTranscriptError, VoiceTurnOrchestrator

router = APIRouter(prefix="/api/learner", tags=["learner"])


class StatePatchRequest(BaseModel):
    action: str = "complete"


class AnswerRequest(BaseModel):
    stateId: str
    answerText: str


def _client(principal: Principal) -> SupabaseUserClient:
    if not principal.access_token:
        raise HTTPException(status_code=401, detail="Missing user access token.")
    return SupabaseUserClient(principal.access_token)


def _load_session(client: SupabaseUserClient, session_id: str, principal: Principal | None = None) -> TrainingSessionDTO:
    user_id = principal.user_id if principal else None
    rows = []
    if session_id in ("active", "current", "default") and user_id:
        rows = client.select("training_sessions", f"select=*&learner_id=eq.{user_id}&status=in.(in_progress,not_started)&order=started_at.desc&limit=1")
        if not rows:
            rows = client.select("training_sessions", f"select=*&learner_id=eq.{user_id}&order=started_at.desc&limit=1")
        if not rows:
            enrollments = client.select("learner_enrollments", f"select=*,company_training_assignments(template_id)&learner_id=eq.{user_id}&limit=1")
            if enrollments:
                enrollment = enrollments[0]
                assignment_info = enrollment.get("company_training_assignments") or {}
                template_id = assignment_info.get("template_id") or "00000000-0000-0000-0000-000000000404"
                states = client.select("training_states", f"select=id&module_id=eq.{enrollment['module_id']}&order=order_index.asc&limit=1")
                if states:
                    created = client.insert(
                        "training_sessions",
                        {
                            "enrollment_id": enrollment["id"],
                            "module_id": enrollment["module_id"],
                            "template_id": template_id,
                            "learner_id": user_id,
                            "company_id": enrollment["company_id"],
                            "current_state_id": states[0]["id"],
                            "status": "in_progress",
                        },
                    )
                    if created:
                        rows = created
    else:
        rows = client.select("training_sessions", f"select=*&id=eq.{session_id}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail="Session not found.")
    real_session_id = rows[0]["id"]
    usage_rows = client.select("session_usage", f"select=*&session_id=eq.{real_session_id}&limit=1")
    return session_from_row(rows[0], usage_from_row(usage_rows[0] if usage_rows else None))


def _load_session_data(client: SupabaseUserClient, session_id: str, principal: Principal | None = None) -> LearnerSessionDataDTO:
    session = _load_session(client, session_id, principal)
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
        category="Atanan egitim",
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


def _stt_provider():
    if STT_PROVIDER and STT_PROVIDER != "elevenlabs":
        raise ElevenLabsSTTConfigurationError("STT_PROVIDER must be elevenlabs.")
    return ElevenLabsSpeechToTextProvider(
        api_key=ELEVENLABS_API_KEY,
        model=ELEVENLABS_STT_MODEL,
        language=ELEVENLABS_STT_LANGUAGE,
        commit_strategy=ELEVENLABS_STT_COMMIT_STRATEGY,
        vad_silence_threshold_secs=ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS,
    )


def _tts_provider():
    if TTS_PROVIDER and TTS_PROVIDER != "elevenlabs":
        raise TextToSpeechError("TTS_PROVIDER must be elevenlabs.")
    return ElevenLabsTextToSpeechProvider(
        api_key=ELEVENLABS_API_KEY,
        voice_id=ELEVENLABS_TTS_VOICE_ID,
        model=ELEVENLABS_TTS_MODEL,
        language=ELEVENLABS_TTS_LANGUAGE,
    )


def _synthesize_turn_tts(session: TrainingSessionDTO, state: TrainingStateDTO, text: str) -> tuple[TextToSpeechResultDTO, bool]:
    provider = _tts_provider()
    from app.services.live_avatar_service import avatar_session_store
    entry = avatar_session_store.get(session.id, state.id)
    avatar_active = bool(entry and "tokenResponse" in entry)
    output_format = "pcm_24000" if avatar_active else "mp3_22050_32"

    try:
        from app.schemas.dtos import TextToSpeechRequestDTO
        tts = provider.synthesize(TextToSpeechRequestDTO(text=text, language=TTS_LANGUAGE, outputFormat=output_format))
        if avatar_active and getattr(tts, "pcmAudioBytes", None):
            from app.services.live_avatar_service import send_avatar_audio
            success = send_avatar_audio(session, state, tts.pcmAudioBytes)
            if not success:
                avatar_active = False
        return tts, avatar_active
    except Exception:
        raise



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
    client = _client(principal)
    rows = client.select("learner_enrollments", f"select=*,company_training_assignments(template_id)&learner_id=eq.{principal.user_id}&order=assigned_at.desc")
    return [
        enrollment_from_row({**row, "template_id": (row.get("company_training_assignments") or {}).get("template_id")})
        for row in rows
    ]


@router.post("/sessions", response_model=TrainingSessionDTO)
def create_session(principal: Principal = Depends(require_role("learner"))) -> TrainingSessionDTO:
    client = _client(principal)
    existing = client.select("training_sessions", f"select=*&learner_id=eq.{principal.user_id}&order=started_at.desc&limit=1")
    if existing:
        return _load_session(client, existing[0]["id"], principal)
    enrollments = client.select("learner_enrollments", f"select=*,company_training_assignments(template_id)&learner_id=eq.{principal.user_id}&status=in.(not_started,in_progress)&limit=1")
    if not enrollments:
        enrollments = client.select("learner_enrollments", f"select=*,company_training_assignments(template_id)&learner_id=eq.{principal.user_id}&order=assigned_at.desc&limit=1")
    if not enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    enrollment = enrollments[0]
    template_id = (enrollment.get("company_training_assignments") or {}).get("template_id")
    if not template_id:
        raise HTTPException(status_code=409, detail="Enrollment assignment is missing a template.")
    states = client.select("training_states", f"select=id&module_id=eq.{enrollment['module_id']}&order=order_index.asc&limit=1")
    if not states:
        raise HTTPException(status_code=404, detail="Training states not found.")
    created = client.insert(
        "training_sessions",
        {
            "enrollment_id": enrollment["id"],
            "module_id": enrollment["module_id"],
            "template_id": template_id,
            "learner_id": principal.user_id,
            "company_id": enrollment["company_id"],
            "current_state_id": states[0]["id"],
            "status": "in_progress",
        },
    )
    if not created:
        raise HTTPException(status_code=502, detail="Session could not be created.")
    return _load_session(client, created[0]["id"], principal)


@router.post("/sessions/restart", response_model=TrainingSessionDTO)
def restart_session(principal: Principal = Depends(require_role("learner"))) -> TrainingSessionDTO:
    client = _client(principal)
    try:
        result = client.rpc("restart_my_latest_training_session", {})
    except Exception as error:
        raise HTTPException(status_code=502, detail={"code": "session_restart_failed", "message": str(error)}) from error
    session_id = result[0] if isinstance(result, list) and result else result
    if not isinstance(session_id, str):
        raise HTTPException(status_code=502, detail={"code": "session_restart_failed", "message": "Restart did not return a session id."})
    return _load_session(client, session_id, principal)


@router.get("/sessions/{session_id}", response_model=LearnerSessionDataDTO)
def get_session(session_id: str, principal: Principal = Depends(require_role("learner"))) -> LearnerSessionDataDTO:
    return _load_session_data(_client(principal), session_id, principal)


@router.patch("/sessions/{session_id}/state", response_model=TrainingSessionDTO)
def patch_session_state(session_id: str, body: StatePatchRequest, principal: Principal = Depends(require_role("learner"))) -> TrainingSessionDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
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
        client.patch("training_sessions", f"id=eq.{session.id}", payload)
    return _load_session(client, session.id, principal)


@router.post("/sessions/{session_id}/conversation-turn", response_model=ConversationTurnResponseDTO)
def post_conversation_turn(session_id: str, body: ConversationTurnRequestDTO, principal: Principal = Depends(require_role("learner"))) -> ConversationTurnResponseDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
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
        client.patch("training_sessions", f"id=eq.{session.id}", {"completed_state_ids": list(completed)})
        session = _load_session(client, session.id, principal)
    tts, avatar_active = _synthesize_turn_tts(session, state, result.assistantText)
    return ConversationTurnResponseDTO(
        session=session,
        stateId=state.id,
        turnNumber=turn_number,
        assistantText=result.assistantText,
        action=result.action,
        conversationComplete=complete,
        guardrail=guardrail,
        providerMetadata=result.providerMetadata,
        tts=tts,
        avatarSessionActive=avatar_active,
    )



@router.post("/sessions/{session_id}/voice/opening", response_model=VoiceOpeningResultDTO)
def start_voice_opening(session_id: str, body: ConversationTurnRequestDTO, principal: Principal = Depends(require_role("learner"))) -> VoiceOpeningResultDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
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


@router.post("/sessions/{session_id}/avatar/token", response_model=LiveAvatarSessionTokenResponseDTO)
def create_avatar_session_token(
    session_id: str,
    body: LiveAvatarSessionTokenRequestDTO,
    principal: Principal = Depends(require_role("learner")),
) -> LiveAvatarSessionTokenResponseDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
    state = next((item for item in states if item.id == body.stateId), None)
    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    try:
        return live_avatar_service.create_avatar_token(session, state)
    except ConversationStateError as error:
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
    except LiveAvatarConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": error.code, "message": str(error)}) from error
    except LiveAvatarProviderError as error:
        raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail={"code": "avatar_token_error", "message": str(error)}) from error


@router.post("/sessions/{session_id}/avatar/session", response_model=LiveAvatarSessionActionResponseDTO)
def handle_avatar_session_action(
    session_id: str,
    body: LiveAvatarSessionActionRequestDTO,
    principal: Principal = Depends(require_role("learner")),
) -> LiveAvatarSessionActionResponseDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
    state = next((item for item in states if item.id == body.stateId), None)


    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    try:
        if body.action == "start":
            return live_avatar_service.start_avatar_session(session, state, body.avatarSessionId)
        elif body.action == "stop":
            return live_avatar_service.stop_avatar_session(session, state, body.avatarSessionId)
        elif body.action == "speak":
            return live_avatar_service.speak_avatar(session, state, body.text or "", body.avatarSessionId)
        raise HTTPException(status_code=422, detail={"code": "invalid_action", "message": f"Unsupported avatar action '{body.action}'."})
    except ConversationStateError as error:
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail={"code": "avatar_session_error", "message": str(error)}) from error



@router.websocket("/sessions/{session_id}/voice/stt")
async def stream_voice_turn(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        start = await websocket.receive_json()
        state_id = start.get("stateId")
        access_token = start.get("accessToken")
        if not isinstance(state_id, str):
            await websocket.send_json({"type": "error", "code": "missing_state_id"})
            await websocket.close(code=1008)
            return
        principal = get_current_principal(
            authorization=f"Bearer {access_token}" if isinstance(access_token, str) and access_token else None,
        )
        if principal.role != "learner":
            await websocket.send_json({"type": "error", "code": "role_not_allowed"})
            await websocket.close(code=1008)
            return

        client = _client(principal)
        session = _load_session(client, session_id, principal)
        states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
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
                        completed = set(session.completedStateIds)
                        completed.add(state.id)
                        client.patch("training_sessions", f"id=eq.{session.id}", {"completed_state_ids": list(completed)})
                    await websocket.send_json({"type": "voice_turn_result", "result": result.model_dump()})
            else:
                await websocket.send_json({"type": event.type, "metadata": event.metadata.model_dump()})
        await websocket.close()
    except ElevenLabsSTTConfigurationError:
        await websocket.send_json({"type": "error", "code": "stt_provider_not_configured"})
        await websocket.close(code=1011)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.send_json({"type": "error", "code": "voice_stream_error"})
        await websocket.close(code=1011)


@router.post("/sessions/{session_id}/answers")
def post_answer(session_id: str, body: AnswerRequest, principal: Principal = Depends(require_role("learner"))) -> dict[str, object]:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    states = [state_from_row(row) for row in client.select("training_states", f"select=*&module_id=eq.{session.moduleId}&order=order_index.asc")]
    state = next((item for item in states if item.id == body.stateId), None)
    if not state:
        raise HTTPException(status_code=404, detail="State not found.")
    session = session_engine.submit_answer(session, body.stateId, body.answerText)
    rubric = rubric_repository.get_rubric_for_state(session.templateId, state.id, state.skillTags)
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
        client.patch("training_sessions", f"id=eq.{session.id}", {"completed_state_ids": list(completed), "current_state_id": session.currentStateId})
    except SupabaseRequestError as error:
        raise HTTPException(status_code=error.status_code, detail="Session progress could not be persisted.") from error
    return {"session": session.model_dump(), "feedback": feedback.model_dump(), "scoringResult": scoring_result.model_dump()}


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeResponseDTO)
def finalize_learner_session(session_id: str, body: FinalizeRequestDTO, principal: Principal = Depends(require_role("learner"))) -> FinalizeResponseDTO:
    try:
        return finalize_session(session_id, body, principal)
    except FinalizationConflictError as error:
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from error
    except FinalizationValidationError as error:
        raise HTTPException(status_code=422, detail={"code": error.code, "message": str(error)}) from error
    except FinalizationError as error:
        raise HTTPException(status_code=502, detail={"code": error.code, "message": str(error)}) from error


@router.get("/sessions/{session_id}/scoring-results", response_model=list[StructuredScoringResultDTO])
def get_session_scoring_results(session_id: str, principal: Principal = Depends(require_role("learner"))) -> list[StructuredScoringResultDTO]:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    return _scoring_results_from_supabase(client, session.id)


@router.get("/sessions/{session_id}/report", response_model=LearnerSessionReportDTO)
def get_session_structured_report(session_id: str, principal: Principal = Depends(require_role("learner"))) -> LearnerSessionReportDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    reports = client.select("reports", f"select=*&session_id=eq.{session.id}&limit=1")
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
        sessionId=session.id,
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


@router.get("/sessions/{session_id}/scoring/{state_id}", response_model=StructuredScoringResultDTO)
def get_scoring_result(session_id: str, state_id: str, principal: Principal = Depends(require_role("learner"))) -> StructuredScoringResultDTO:
    client = _client(principal)
    session = _load_session(client, session_id, principal)
    result = next((item for item in _scoring_results_from_supabase(client, session.id) if item.stateId == state_id), None)
    if not result:
        raise HTTPException(status_code=404, detail="Scoring result not found.")
    return result


@router.get("/reports/{session_id}", response_model=ReportDTO)
def get_report(session_id: str, principal: Principal = Depends(require_role("learner"))) -> ReportDTO:
    client = _client(principal)
    from app.db.supabase_mappers import report_from_row
    session = _load_session(client, session_id, principal)
    rows = client.select("reports", f"select=*&session_id=eq.{session.id}&limit=1")
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report_from_row(rows[0])
