import threading
import time
from app.services.voice_poc_metrics import voice_poc_metrics
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
    LiveAvatarPartialAudioError,
    LiveAvatarProvider,
    get_live_avatar_provider,
)


class ActiveAvatarSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._locks = tuple(threading.RLock() for _ in range(64))
        self._expiry_timers: dict[str, threading.Timer] = {}

    def _key(self, session_id: str, state_id: str) -> str:
        return f"avatar:{session_id}:{state_id}"

    def get_lock(self, session_id: str, state_id: str) -> threading.RLock:
        key = self._key(session_id, state_id)
        return self._locks[hash(key) % len(self._locks)]

    def register_start(self, session_id: str, state_id: str, avatar_session_id: str) -> dict[str, Any]:
        key = self._key(session_id, state_id)
        now = time.time()
        with self.get_lock(session_id, state_id):
            existing = self._sessions.get(key)
            if existing:
                if avatar_session_id and avatar_session_id != existing["avatarSessionId"]:
                    raise ConversationStateError("A different avatar session is already active.")
                existing["lastActiveAt"] = now
                existing["openCount"] = 1
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

    def register_stop(self, session_id: str, state_id: str, avatar_session_id: str | None = None) -> dict[str, Any] | None:
        key = self._key(session_id, state_id)
        with self.get_lock(session_id, state_id):
            entry = self._sessions.get(key)
            if not entry or (avatar_session_id and entry["avatarSessionId"] != avatar_session_id):
                return None
            
            entry["openCount"] = max(0, entry.get("openCount", 1) - 1)
            if entry["openCount"] > 0:
                return entry

            self._sessions.pop(key, None)
            timer = self._expiry_timers.pop(key, None)
            if timer:
                timer.cancel()
            started = entry.get("startedAt", time.time())
            entry["activeSeconds"] = round(time.time() - started, 2)
            
        return entry

    def get(self, session_id: str, state_id: str) -> dict[str, Any] | None:
        return self._sessions.get(self._key(session_id, state_id))

    def get_token(self, session_id: str, state_id: str) -> LiveAvatarSessionTokenResponseDTO | None:
        entry = self.get(session_id, state_id)
        if entry and "tokenResponse" in entry:
            token = entry["tokenResponse"]
            if time.time() - entry["startedAt"] < token.sessionTimeoutSec:
                return token
            self.register_stop(session_id, state_id)

        return None

    def schedule_expiry(self, session_id: str, state_id: str, entry: dict[str, Any], seconds: int) -> None:
        key = self._key(session_id, state_id)

        def expire() -> None:
            with self.get_lock(session_id, state_id):
                if self._sessions.get(key) is entry:
                    self.register_stop(session_id, state_id, entry["avatarSessionId"])

        timer = threading.Timer(seconds, expire)
        timer.daemon = True
        self._expiry_timers[key] = timer
        timer.start()

    def clear(self) -> None:
        for timer in list(self._expiry_timers.values()):
            timer.cancel()
        self._expiry_timers.clear()
        self._sessions.clear()


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
        store.schedule_expiry(session.id, state.id, entry, token_resp.sessionTimeoutSec)
        voice_poc_metrics.record(session.id, state.id, "avatar_start")
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
    with store.get_lock(session.id, state.id):
        token = store.get_token(session.id, state.id)
        if token is None:
            raise ConversationStateError("Create an avatar token before starting the session.")
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
        entry = store.register_stop(session.id, state.id, avatar_session_id)
        target_session_id = avatar_session_id or (entry.get("avatarSessionId") if entry else "")
        if target_session_id and entry:
            try:
                stopped = active_provider.stop_session(target_session_id)
                if stopped:
                    voice_poc_metrics.record(session.id, state.id, "avatar_stop", duration_seconds=entry.get("activeSeconds", 0.0))
                else:
                    voice_poc_metrics.record(session.id, state.id, "error")
            except Exception:
                voice_poc_metrics.record(session.id, state.id, "error")
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
    cancel_event=None,
) -> bool:
    if not pcm_audio:
        return False
        
    with store.get_lock(session.id, state.id):
        token_resp = store.get_token(session.id, state.id)
        if not token_resp:
            return False
        ws_url = token_resp.metadata.get("wsUrl") if token_resp.metadata else None
        if not ws_url:
            return False
        active_provider = provider or get_live_avatar_provider()
        try:
            return active_provider.send_audio(ws_url, pcm_audio, cancel_event=cancel_event) if cancel_event is not None else active_provider.send_audio(ws_url, pcm_audio)
        except LiveAvatarPartialAudioError:
            raise
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


def send_avatar_audio_stream(session, state, chunks, cancel_event, provider=None, store=avatar_session_store):
    # Do not hold the store lock during network reads: stop must remain responsive.
    with store.get_lock(session.id, state.id):
        token = store.get_token(session.id, state.id)
        ws_url = token.metadata.get("wsUrl") if token and token.metadata else None
    if not ws_url or cancel_event.is_set():
        return False
    return (provider or get_live_avatar_provider()).send_audio_stream(ws_url, chunks, cancel_event)
