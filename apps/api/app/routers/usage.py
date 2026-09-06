from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import Principal, get_current_principal
from app.db.supabase_mappers import usage_from_row
from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import SessionCostLogDTO, SessionEventLogDTO, SessionUsageDTO

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/session/{session_id}", response_model=SessionUsageDTO)
def get_session_usage(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionUsageDTO:
    if not principal.access_token:
        raise RuntimeError("Missing user access token.")
    client = SupabaseUserClient(principal.access_token)
    real_session_id = session_id
    if session_id in ("active", "current", "default"):
        active_sessions = client.select("training_sessions", f"select=id&learner_id=eq.{principal.user_id}&status=in.(in_progress,not_started)&order=started_at.desc&limit=1")
        if not active_sessions:
            active_sessions = client.select("training_sessions", f"select=id&learner_id=eq.{principal.user_id}&order=started_at.desc&limit=1")
        if active_sessions:
            real_session_id = active_sessions[0]["id"]
    rows = client.select("session_usage", f"select=*&session_id=eq.{real_session_id}&limit=1")
    return usage_from_row(rows[0] if rows else None)



@router.post("/session/{session_id}/events", response_model=SessionEventLogDTO)
def create_session_event(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionEventLogDTO:
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


@router.post("/session/{session_id}/cost-log", response_model=SessionCostLogDTO)
def create_cost_log(session_id: str, principal: Principal = Depends(get_current_principal)) -> SessionCostLogDTO:
    raise HTTPException(status_code=501, detail="User-scoped cost log writes are disabled; server-side cost persistence is deferred.")
