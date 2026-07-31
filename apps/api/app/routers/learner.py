from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_role
from app.schemas.dtos import EnrollmentDTO, ReportDTO, StructuredScoringResultDTO, TrainingSessionDTO
from app.services import mock_store
from app.services import rubric_repository
from app.services import scoring_repository
from app.services import scoring_service
from app.services import session_engine
from app.services.scoring_errors import AnswerGuardrailError, InvalidProviderOutputError, InvalidRubricError, MaxQueriesPerStateError, ProviderRetryExhaustedError

router = APIRouter(prefix="/api/learner", tags=["learner"], dependencies=[Depends(require_role("learner"))])


class StatePatchRequest(BaseModel):
    action: str = "complete"


class AnswerRequest(BaseModel):
    stateId: str
    answerText: str


@router.get("/trainings", response_model=list[EnrollmentDTO])
def get_learner_trainings() -> list[EnrollmentDTO]:
    return mock_store.enrollments


@router.post("/sessions", response_model=TrainingSessionDTO)
def create_session() -> TrainingSessionDTO:
    mock_store.sessions["demo-session-1"] = mock_store.clone_session()
    return mock_store.sessions["demo-session-1"]


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session": session.model_dump(), "states": [state.model_dump() for state in mock_store.training_states]}


@router.patch("/sessions/{session_id}/state", response_model=TrainingSessionDTO)
def patch_session_state(session_id: str, body: StatePatchRequest) -> TrainingSessionDTO:
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
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


@router.post("/sessions/{session_id}/answers")
def post_answer(session_id: str, body: AnswerRequest) -> dict[str, object]:
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
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


@router.get("/sessions/{session_id}/scoring/{state_id}", response_model=StructuredScoringResultDTO)
def get_scoring_result(session_id: str, state_id: str) -> StructuredScoringResultDTO:
    session = mock_store.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    result = scoring_repository.get_scoring_result(session_id, state_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scoring result not found.")
    return result


@router.get("/reports/{session_id}", response_model=ReportDTO)
def get_report(session_id: str) -> ReportDTO:
    if session_id != mock_store.demo_report.sessionId:
        raise HTTPException(status_code=404, detail="Report not found.")
    return mock_store.demo_report
