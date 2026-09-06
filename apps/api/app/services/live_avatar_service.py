import threading
import time
from typing import Any

from app.schemas.dtos import (
    LiveAvatarSessionActionRequestDTO,
    LiveAvatarSessionActionResponseDTO,
    LiveAvatarSessionTokenResponseDTO,
    ProviderMetadataDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
)
from app.services.conversation_errors import ConversationStateError
from app.services.live_avatar_provider import (
    LiveAvatarError,
    LiveAvatarProvider,
    get_live_avatar_provider,
)


class ActiveAvatarSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._global_lock = threading.Lock()

    def _key(self, session_id: str, state_id: str) -> str:
        return f"avatar:{session_id}:{state_id}"

    def get_lock(self, session_id: str, state_id: str) -> threading.RLock:
        key = self._key(session_id, state_id)
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    def register_start(self, session_id: str, state_id: str, avatar_session_id: str) -> dict[str, Any]:
        key = self._key(session_id, state_id)
        now = time.time()
        with self.get_lock(session_id, state_id):
            existing = self._sessions.get(key)
            if existing:
                existing["avatarSessionId"] = avatar_session_id or existing.get("avatarSessionId", "")
                existing["lastActiveAt"] = now
                existing["openCount"] = existing.get("openCount", 1) + 1
                return existing
            entry = {
                "sessionId": session_id,
                "stateId": state_id,
                "avatarSessionId": avatar_session_id or f"avatar-sess-{session_id[:8]}-{int(now)}",
                "startedAt": now,
                "lastActiveAt": now,
                "openCount": 1,
                "activeSeconds": 0.0,
            }
            self._sessions[key] = entry
            return entry

    def register_stop(self, session_id: str, state_id: str) -> dict[str, Any] | None:
        key = self._key(session_id, state_id)
        with self.get_lock(session_id, state_id):
            entry = self._sessions.get(key)
            if not entry:
                return None
            
            entry["openCount"] = max(0, entry.get("openCount", 1) - 1)
            if entry["openCount"] > 0:
                return entry

            self._sessions.pop(key, None)
            started = entry.get("startedAt", time.time())
            entry["activeSeconds"] = round(time.time() - started, 2)
            
        with self._global_lock:
            self._locks.pop(key, None)
        return entry

    def get(self, session_id: str, state_id: str) -> dict[str, Any] | None:
        return self._sessions.get(self._key(session_id, state_id))

    def get_token(self, session_id: str, state_id: str) -> LiveAvatarSessionTokenResponseDTO | None:
        entry = self.get(session_id, state_id)
        if entry and "tokenResponse" in entry:
            return entry["tokenResponse"]
        return None

    def clear(self) -> None:
        self._sessions.clear()
        with self._global_lock:
            self._locks.clear()


avatar_session_store = ActiveAvatarSessionStore()


def verify_avatar_state(session: TrainingSessionDTO, state: TrainingStateDTO) -> None:
    if not (state.avatarEnabled or state.type in {"avatar", "live_avatar", "roleplay"}):
        raise ConversationStateError("State is not configured for LiveAvatar.")



def create_avatar_token(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    provider: LiveAvatarProvider | None = None,
    store: ActiveAvatarSessionStore = avatar_session_store,
) -> LiveAvatarSessionTokenResponseDTO:
    verify_avatar_state(session, state)
    with store.get_lock(session.id, state.id):
        existing = store.get_token(session.id, state.id)
        if existing:
            return existing

        active_provider = provider or get_live_avatar_provider()
        token_resp = active_provider.create_session_token(state.id)
        
        avatar_session_id = token_resp.metadata.get("avatarSessionId", "") if token_resp.metadata else ""
        entry = store.register_start(session.id, state.id, avatar_session_id)
        entry["tokenResponse"] = token_resp
        return token_resp


def start_avatar_session(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    avatar_session_id: str | None = None,
    provider: LiveAvatarProvider | None = None,
    store: ActiveAvatarSessionStore = avatar_session_store,
) -> LiveAvatarSessionActionResponseDTO:
    verify_avatar_state(session, state)
    active_provider = provider or get_live_avatar_provider()
    entry = store.register_start(session.id, state.id, avatar_session_id or "")
    return LiveAvatarSessionActionResponseDTO(
        status="started",
        stateId=state.id,
        avatarSessionId=entry["avatarSessionId"],
        activeSeconds=0.0,
        providerMetadata=ProviderMetadataDTO(
            provider=getattr(active_provider, "provider_name", "live_avatar"),
            model=getattr(active_provider, "avatar_id", "default"),
        ),
    )


def stop_avatar_session(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    avatar_session_id: str | None = None,
    provider: LiveAvatarProvider | None = None,
    store: ActiveAvatarSessionStore = avatar_session_store,
) -> LiveAvatarSessionActionResponseDTO:
    active_provider = provider or get_live_avatar_provider()
    with store.get_lock(session.id, state.id):
        entry = store.register_stop(session.id, state.id)
        target_session_id = avatar_session_id or (entry.get("avatarSessionId") if entry else "")
        if target_session_id and (not entry or entry.get("openCount", 0) == 0):
            try:
                active_provider.stop_session(target_session_id)
            except Exception:
                pass
        active_seconds = entry.get("activeSeconds", 0.0) if entry else 0.0
        return LiveAvatarSessionActionResponseDTO(
            status="stopped",
            stateId=state.id,
            avatarSessionId=target_session_id,
            activeSeconds=active_seconds,
            providerMetadata=ProviderMetadataDTO(
                provider=getattr(active_provider, "provider_name", "live_avatar"),
                model=getattr(active_provider, "avatar_id", "default"),
            ),
        )


def send_avatar_audio(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    pcm_audio: bytes,
    provider: LiveAvatarProvider | None = None,
    store: ActiveAvatarSessionStore = avatar_session_store,
) -> bool:
    if not pcm_audio:
        return False
        
    entry = store.get(session.id, state.id)
    if not entry or "tokenResponse" not in entry:
        return False
        
    token_resp = entry["tokenResponse"]
    ws_url = token_resp.metadata.get("wsUrl") if token_resp.metadata else None
    if not ws_url:
        return False
        
    active_provider = provider or get_live_avatar_provider()
    try:
        return active_provider.send_audio(ws_url, pcm_audio)
    except Exception:
        return False

def speak_avatar(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    text: str,
    avatar_session_id: str | None = None,
    provider: LiveAvatarProvider | None = None,
    store: ActiveAvatarSessionStore = avatar_session_store,
) -> LiveAvatarSessionActionResponseDTO:
    active_provider = provider or get_live_avatar_provider()
    entry = store.get(session.id, state.id)
    target_session_id = avatar_session_id or (entry.get("avatarSessionId") if entry else "")
    if not target_session_id:
        return LiveAvatarSessionActionResponseDTO(
            status="fallback",
            stateId=state.id,
            avatarSessionId="",
            activeSeconds=entry.get("activeSeconds", 0.0) if entry else 0.0,
            errorMessage="No active avatar session found to speak.",
            providerMetadata=ProviderMetadataDTO(
                provider=getattr(active_provider, "provider_name", "live_avatar"),
                model=getattr(active_provider, "avatar_id", "default"),
            ),
        )
    if text:
        try:
            active_provider.speak_session(target_session_id, text)
        except Exception:
            pass
    active_seconds = entry.get("activeSeconds", 0.0) if entry else 0.0
    return LiveAvatarSessionActionResponseDTO(
        status="speaking",
        stateId=state.id,
        avatarSessionId=target_session_id,
        activeSeconds=active_seconds,
        providerMetadata=ProviderMetadataDTO(
            provider=getattr(active_provider, "provider_name", "live_avatar"),
            model=getattr(active_provider, "avatar_id", "default"),
        ),
    )
