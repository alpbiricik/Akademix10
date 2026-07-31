from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.security import Role, get_mock_role_from_header
from app.schemas.dtos import SessionCostLogDTO, SessionEventLogDTO, SessionUsageDTO
from app.services import mock_store

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/session/{session_id}", response_model=SessionUsageDTO)
def get_session_usage(session_id: str, role: Role = Depends(get_mock_role_from_header)) -> SessionUsageDTO:
    _ = role
    session = mock_store.sessions.get(session_id, mock_store.demo_session)
    return session.usage


@router.post("/session/{session_id}/events", response_model=SessionEventLogDTO)
def create_session_event(session_id: str, role: Role = Depends(get_mock_role_from_header)) -> SessionEventLogDTO:
    _ = role
    return SessionEventLogDTO(
        id=f"event-{int(datetime.now(timezone.utc).timestamp())}",
        sessionId=session_id,
        companyId="company-demo",
        learnerUserId="user-learner-demo",
        stateId=None,
        eventType="state_started",
        payload={"mock": True},
        occurredAt=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/session/{session_id}/cost-log", response_model=SessionCostLogDTO)
def create_cost_log(session_id: str, role: Role = Depends(get_mock_role_from_header)) -> SessionCostLogDTO:
    _ = role
    return SessionCostLogDTO(
        id=f"cost-log-{int(datetime.now(timezone.utc).timestamp())}",
        sessionId=session_id,
        companyId="company-demo",
        avatarActiveSeconds=420,
        avatarOpenCount=10,
        bufferedBillableAvatarMin=8.05,
        estimatedCostUsd=0.8,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
