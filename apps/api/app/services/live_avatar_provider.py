import json
import time
import urllib.error
import urllib.request
import uuid
import base64
import threading
from typing import Any, Protocol

try:
    from websockets.sync.client import connect
except ImportError:
    connect = None

from app.core.config import (
    HEYGEN_API_KEY,
    HEYGEN_AVATAR_ID,
    HEYGEN_QUALITY,
    HEYGEN_VOICE_ID,
    LIVE_AVATAR_MAX_SESSION_SECONDS,
    LIVE_AVATAR_PROVIDER,
    LIVE_AVATAR_SANDBOX,
    LIVE_AVATAR_SANDBOX_AVATAR_ID,
)
from app.schemas.dtos import (
    LiveAvatarSessionActionResponseDTO,
    LiveAvatarSessionTokenResponseDTO,
    ProviderMetadataDTO,
)

PCM_BYTES_PER_SECOND = 24000 * 2
PCM_FRAME_BYTES = 4800


def _pcm_frames(chunks, frame_bytes: int = PCM_FRAME_BYTES):
    """Reframe arbitrary PCM chunks while buffering at most one output frame."""
    pending = bytearray()
    for chunk in chunks:
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise ValueError("Invalid PCM chunk")
        view = memoryview(chunk)
        offset = 0
        while offset < len(view):
            take = min(frame_bytes - len(pending), len(view) - offset)
            pending.extend(view[offset:offset + take])
            offset += take
            if len(pending) == frame_bytes:
                yield bytes(pending)
                pending.clear()
    if len(pending) % 2:
        raise ValueError("PCM16 audio ended on a partial sample")
    if pending:
        yield bytes(pending)


def _wait_for_audio_deadline(deadline: float, frame_bytes: int, cancel_event=None) -> float:
    """Pace against a monotonic timeline without adding network send time."""
    frame_duration = frame_bytes / PCM_BYTES_PER_SECOND
    deadline += frame_duration
    now = time.monotonic()
    if now - deadline > frame_duration:
        # Reset after a long stall instead of sending a burst to catch up.
        deadline = now
    delay = max(0.0, deadline - now)
    if delay:
        if cancel_event:
            if cancel_event.wait(delay):
                raise LiveAvatarPartialAudioError("Audio cancelled.")
        else:
            time.sleep(delay)
    return deadline


class LiveAvatarError(Exception):
    code = "live_avatar_error"


class LiveAvatarConfigurationError(LiveAvatarError):
    code = "live_avatar_not_configured"


class LiveAvatarProviderError(LiveAvatarError):
    code = "live_avatar_provider_error"


class LiveAvatarPartialAudioError(LiveAvatarError):
    code = "avatar_partial_audio"


class LiveAvatarProvider(Protocol):
    provider_name: str

    def create_session_token(self, state_id: str) -> LiveAvatarSessionTokenResponseDTO:
        ...

    def stop_session(self, avatar_session_id: str) -> bool:
        ...

    def send_audio(self, ws_url: str, pcm_audio: bytes) -> bool:
        ...


class HeyGenLiveAvatarProvider:
    provider_name = "heygen"
    api_base_url = "https://api.liveavatar.com/v1"

    def __init__(
        self,
        api_key: str,
        avatar_id: str = "",
        voice_id: str = "",
        quality: str = "medium",
        timeout_sec: int = 600,
    ) -> None:
        if not api_key:
            raise LiveAvatarConfigurationError("HeyGen LiveAvatar requires a server-side API key.")
        self._api_key = api_key
        self.avatar_id = avatar_id or "default"
        self.voice_id = voice_id
        self.quality = quality or "medium"
        self.timeout_sec = timeout_sec or LIVE_AVATAR_MAX_SESSION_SECONDS

    def create_session_token(self, state_id: str) -> LiveAvatarSessionTokenResponseDTO:
        started = time.perf_counter()
        token_url = f"{self.api_base_url}/sessions/token"
        
        token_payload: dict[str, Any] = {
            "mode": "LITE",
        }
        
        if LIVE_AVATAR_SANDBOX:
            token_payload["is_sandbox"] = True
            token_payload["avatar_id"] = LIVE_AVATAR_SANDBOX_AVATAR_ID
        else:
            token_payload["avatar_id"] = self.avatar_id

        if self.voice_id:
            token_payload["avatar_persona"] = {
                "voice_id": self.voice_id,
                "language": "tr",
            }


        req = urllib.request.Request(
            token_url,
            data=json.dumps(token_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": self._api_key,
                "User-Agent": "AkademX10-LiveAvatar/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            raise LiveAvatarProviderError("LiveAvatar session token creation failed.") from None

        data = body.get("data") or {}
        session_token = data.get("session_token") or data.get("token") or body.get("token")
        session_id = data.get("session_id")
        if not session_token:
            raise LiveAvatarProviderError("HeyGen response did not include a streaming session token.")

        livekit_url = None
        livekit_client_token = None
        ws_url = None
        fallback_reason = None
        error_message = None
        try:
            start_req = urllib.request.Request(
                f"{self.api_base_url}/sessions/start",
                data=b"{}",
                headers={
                    "Authorization": f"Bearer {session_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "AkademX10-LiveAvatar/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(start_req, timeout=15) as start_resp:
                start_data = json.loads(start_resp.read().decode("utf-8")).get("data") or {}
                livekit_url = start_data.get("livekit_url")
                livekit_client_token = start_data.get("livekit_client_token")
                ws_url = start_data.get("ws_url")
                session_id = start_data.get("session_id") or session_id
        except urllib.error.HTTPError:
            error_message = "LiveAvatar session start failed."
        except Exception:
            error_message = "LiveAvatar session start failed."

        if not livekit_url or not livekit_client_token:
            raise LiveAvatarProviderError(error_message or "LiveAvatar did not return LiveKit connection details.")
        if session_id and ws_url:
            with self._ws_pool_lock:
                self._session_urls[session_id] = ws_url
                timer = threading.Timer(self.timeout_sec, self.stop_session, args=(session_id,))
                timer.daemon = True
                previous = self._session_timers.pop(session_id, None)
                if previous:
                    previous.cancel()
                self._session_timers[session_id] = timer
                timer.start()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LiveAvatarSessionTokenResponseDTO(
            provider=self.provider_name,
            sessionToken=session_token,
            avatarId=self.avatar_id,
            voiceId=self.voice_id,
            quality=self.quality,
            sessionTimeoutSec=self.timeout_sec,
            metadata={
                "latencyMs": latency_ms,
                "avatarSessionId": session_id,
                "livekitUrl": livekit_url,
                "livekitClientToken": livekit_client_token,
                "wsUrl": ws_url,
                "fallbackReason": fallback_reason,
                "errorMessage": error_message,
            },
        )


    _ws_pool: dict[str, Any] = {}
    _ws_pool_lock = threading.RLock()
    # Providers are constructed per request; ownership must outlive an instance.
    _session_urls: dict[str, str] = {}
    _session_timers: dict[str, threading.Timer] = {}
    # Fixed stripes bound lock memory and serialize complete audio utterances.
    _send_locks = tuple(threading.RLock() for _ in range(64))

    def _receive_events(self, ws_url: str, ws: Any) -> None:
        # Keep draining provider events while speaking AND between turns. A full
        # receive queue blocks socket reads, including keepalive pong frames.
        try:
            while True:
                ws.recv()
        except Exception:
            pass
        finally:
            with self._ws_pool_lock:
                if self._ws_pool.get(ws_url) is ws:
                    self._ws_pool.pop(ws_url, None)
            try:
                ws.close()
            except Exception:
                pass

    def _wait_for_lite_connected(self, ws: Any, timeout_sec: float = 8.0) -> bool:
        deadline = time.perf_counter() + timeout_sec
        while time.perf_counter() < deadline:
            remaining = max(0.1, deadline - time.perf_counter())
            try:
                raw = ws.recv(timeout=remaining)
            except TypeError:
                # Older websockets sync clients may not support timeout here.
                # Fail readiness rather than blocking indefinitely or sending early.
                return False
            except Exception:
                return False

            try:
                message = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if message.get("type") == "session.state_updated" and message.get("state") == "connected":
                return True
        return False

    def _close_session_socket(self, avatar_session_id: str) -> None:
        with self._ws_pool_lock:
            ws_url = self._session_urls.pop(avatar_session_id, None)
            timer = self._session_timers.pop(avatar_session_id, None)
            if timer:
                timer.cancel()
        if ws_url:
            with self._send_locks[hash(ws_url) % len(self._send_locks)]:
                with self._ws_pool_lock:
                    ws = self._ws_pool.pop(ws_url, None)
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

    def stop_session(self, avatar_session_id: str) -> bool:
        if not avatar_session_id:
            return True
        self._close_session_socket(avatar_session_id)

        url = f"{self.api_base_url}/sessions/stop"
        payload = json.dumps({"session_id": avatar_session_id}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": self._api_key,
                "User-Agent": "AkademX10-LiveAvatar/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status in {200, 204}
        except Exception:
            return False

    def send_audio(self, ws_url: str, pcm_audio: bytes, cancel_event=None) -> bool:
        with self._send_locks[hash(ws_url) % len(self._send_locks)]:
            return self._send_audio_locked(ws_url, pcm_audio, cancel_event)

    def _send_audio_locked(self, ws_url: str, pcm_audio: bytes, cancel_event=None) -> bool:
        if not ws_url or not pcm_audio:
            return False
        if not connect:
            return False

        event_id = str(uuid.uuid4())
        chunk_index = 0
        ws = None
        try:
            with self._ws_pool_lock:
                ws = self._ws_pool.get(ws_url)
            if ws is None:
                ws = connect(ws_url, open_timeout=10, close_timeout=2)
                if not self._wait_for_lite_connected(ws):
                    ws.close()
                    return False
                with self._ws_pool_lock:
                    pooled = self._ws_pool.setdefault(ws_url, ws)
                if pooled is ws:
                    threading.Thread(
                        target=self._receive_events, args=(ws_url, ws), daemon=True,
                        name="live-avatar-events",
                    ).start()
                else:
                    ws.close()
                    ws = pooled

            frames = iter(_pcm_frames((pcm_audio,)))
            chunk = next(frames, None)
            deadline = time.monotonic()
            while chunk is not None:
                if cancel_event and cancel_event.is_set():
                    raise LiveAvatarPartialAudioError("Audio cancelled.")
                speak_msg = {
                    "type": "agent.speak",
                    "event_id": f"{event_id}-{chunk_index}",
                    "audio": base64.b64encode(chunk).decode("ascii"),
                }
                ws.send(json.dumps(speak_msg))
                chunk_index += 1
                next_chunk = next(frames, None)
                if next_chunk is not None:
                    deadline = _wait_for_audio_deadline(deadline, len(chunk), cancel_event)
                chunk = next_chunk

            # Signal end of audio
            end_msg = {
                "type": "agent.speak_end",
                "event_id": event_id,
            }
            ws.send(json.dumps(end_msg))
            return True
        except Exception:
            with self._ws_pool_lock:
                if self._ws_pool.get(ws_url) is ws:
                    self._ws_pool.pop(ws_url, None)
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
            if chunk_index:
                raise LiveAvatarPartialAudioError("Audio interrupted after delivery began.") from None
            return False

    def send_audio_stream(self, ws_url, chunks, cancel_event) -> bool:
        """Same PCM/event contract as buffered audio; no full utterance retained."""
        with self._send_locks[hash(ws_url) % len(self._send_locks)]:
            ws = None
            try:
                with self._ws_pool_lock:
                    ws = self._ws_pool.get(ws_url)
                if ws is None:
                    ws = connect(ws_url, open_timeout=10, close_timeout=2)
                    if not self._wait_for_lite_connected(ws):
                        ws.close()
                        return False
                    with self._ws_pool_lock:
                        self._ws_pool[ws_url] = ws
                    threading.Thread(target=self._receive_events, args=(ws_url, ws), daemon=True, name="live-avatar-events").start()
                event_id = str(uuid.uuid4())
                sent = False
                index = 0
                frames = iter(_pcm_frames(chunks))
                chunk = next(frames, None)
                deadline = time.monotonic()
                while chunk is not None:
                    if cancel_event.is_set():
                        break
                    ws.send(json.dumps({"type": "agent.speak", "event_id": f"{event_id}-{index}", "audio": base64.b64encode(chunk).decode("ascii")}))
                    sent = True
                    index += 1
                    next_chunk = next(frames, None)
                    if next_chunk is not None:
                        deadline = _wait_for_audio_deadline(deadline, len(chunk), cancel_event)
                    chunk = next_chunk
                if cancel_event.is_set():
                    raise RuntimeError("Cancelled")
                ws.send(json.dumps({"type": "agent.speak_end", "event_id": event_id}))
                return sent
            except Exception:
                with self._ws_pool_lock:
                    if self._ws_pool.get(ws_url) is ws:
                        self._ws_pool.pop(ws_url, None)
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass
                raise


def get_live_avatar_provider() -> LiveAvatarProvider:
    if LIVE_AVATAR_PROVIDER and LIVE_AVATAR_PROVIDER != "heygen":
        raise LiveAvatarConfigurationError("LIVE_AVATAR_PROVIDER must be heygen.")
    return HeyGenLiveAvatarProvider(
        api_key=HEYGEN_API_KEY,
        avatar_id=HEYGEN_AVATAR_ID,
        voice_id=HEYGEN_VOICE_ID,
        quality=HEYGEN_QUALITY,
        timeout_sec=LIVE_AVATAR_MAX_SESSION_SECONDS,
    )
