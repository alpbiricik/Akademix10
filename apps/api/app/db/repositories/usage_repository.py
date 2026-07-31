from datetime import datetime, timezone

from app.schemas.dtos import SessionCostLogDTO, SessionEventLogDTO
from app.services import mock_store


class UsageRepository:
    """Usage and audit persistence boundary backed by mock_store for Phase 2G."""

    def get_session_usage(self, session_id: str):
        session = mock_store.sessions.get(session_id, mock_store.demo_session)
        return session.usage

    def save_event_log(self, session_id: str, event_type: str = "state_started", payload: dict | None = None):
        return SessionEventLogDTO(
            id=f"event-{int(datetime.now(timezone.utc).timestamp())}",
            sessionId=session_id,
            companyId="company-demo",
            learnerUserId="user-learner-demo",
            stateId=None,
            eventType=event_type,
            payload=payload or {"mock": True},
            occurredAt=datetime.now(timezone.utc).isoformat(),
        )

    def save_cost_log(self, session_id: str, metadata: dict | None = None):
        return SessionCostLogDTO(
            id=f"cost-log-{int(datetime.now(timezone.utc).timestamp())}",
            sessionId=session_id,
            companyId="company-demo",
            avatarActiveSeconds=420,
            avatarOpenCount=10,
            bufferedBillableAvatarMin=8.05,
            estimatedCostUsd=0.8,
            metadata=metadata or {"mock": True},
            createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def update_session_usage(self, session_id: str, usage):
        # TODO: update aggregated session_usage row in Supabase.
        _ = session_id
        return usage
