from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import Principal, get_current_principal
from app.db.database import DatabaseMode, get_database_mode
from app.db.supabase_mappers import usage_from_row
from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import SessionCostLogDTO, SessionEventLogDTO, SessionUsageDTO
from app.services import mock_store

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/session/{session_id}", response_model=SessionUsageDTO)
def get_session_usage(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionUsageDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        if not principal.access_token:
            raise RuntimeError("Missing user access token.")
        rows = SupabaseUserClient(principal.access_token).select("session_usage", f"select=*&session_id=eq.{session_id}&limit=1")
        return usage_from_row(rows[0] if rows else None)
    session = mock_store.sessions.get(session_id, mock_store.demo_session)
    return session.usage


@router.post("/session/{session_id}/events", response_model=SessionEventLogDTO)
def create_session_event(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionEventLogDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        if not principal.access_token:
            raise RuntimeError("Missing user access token.")
        client = SupabaseUserClient(principal.access_token)
        sessions = client.select("training_sessions", f"select=company_id,learner_id&id=eq.{session_id}&limit=1")
        if not sessions:
            raise HTTPException(status_code=404, detail="Session not found.")
        row = client.insert("session_event_logs", {"session_id": session_id, "user_id": principal.user_id, "event_type": "state_started", "event_payload": {"source": "api"}})[0]
        return SessionEventLogDTO(
            id=row["id"],
            sessionId=session_id,
            companyId=sessions[0]["company_id"],
            learnerUserId=sessions[0]["learner_id"],
            stateId=row.get("state_id"),
            eventType="state_started",
            payload=row.get("event_payload") or {},
            occurredAt=row.get("created_at") or "",
        )
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
def create_cost_log(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionCostLogDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        raise HTTPException(status_code=501, detail="User-scoped cost log writes are disabled; server-side cost persistence is deferred.")
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
