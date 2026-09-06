import json
import time
import urllib.error
import urllib.request
import uuid
import base64
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


class LiveAvatarError(Exception):
    code = "live_avatar_error"


class LiveAvatarConfigurationError(LiveAvatarError):
    code = "live_avatar_not_configured"


class LiveAvatarProviderError(LiveAvatarError):
    code = "live_avatar_provider_error"


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
            raise LiveAvatarProviderError(f"HeyGen streaming token creation failed: {error}") from error

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
        except urllib.error.HTTPError as error:
            try:
                err_body = json.loads(error.read().decode("utf-8"))
                error_message = err_body.get("message") or str(error)
                if err_body.get("code") == 4033 or "credit" in error_message.lower():
                    fallback_reason = "no_credits"
            except Exception:
                error_message = str(error)
        except Exception as error:
            error_message = str(error)

        if not livekit_url or not livekit_client_token:
            raise LiveAvatarProviderError(error_message or "LiveAvatar did not return LiveKit connection details.")
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

    def _wait_for_lite_connected(self, ws: Any, timeout_sec: float = 8.0) -> bool:
        deadline = time.perf_counter() + timeout_sec
        while time.perf_counter() < deadline:
            remaining = max(0.1, deadline - time.perf_counter())
            try:
                raw = ws.recv(timeout=remaining)
            except TypeError:
                # Older websockets sync clients may not support timeout here.
                # In that case, avoid blocking indefinitely and continue.
                return True
            except Exception:
                return False

            try:
                message = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if message.get("type") == "session.state_updated" and message.get("state") == "connected":
                return True
        return False

    def stop_session(self, avatar_session_id: str) -> bool:
        if not avatar_session_id:
            return True
        # Close persistent WS if any
        keys_to_remove = []
        for ws_url, ws in self._ws_pool.items():
            try:
                ws.close()
            except Exception:
                pass
            keys_to_remove.append(ws_url)
        for k in keys_to_remove:
            self._ws_pool.pop(k, None)

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

    def send_audio(self, ws_url: str, pcm_audio: bytes) -> bool:
        if not ws_url or not pcm_audio:
            return False
        if not connect:
            return False

        # PCM16 mono 24kHz = 48000 bytes per second
        # Stream in ~100ms chunks for real-time pacing so the avatar
        # can animate lip-sync as audio arrives
        SAMPLE_RATE = 24000
        BYTES_PER_SAMPLE = 2  # 16-bit
        BYTES_PER_SEC = SAMPLE_RATE * BYTES_PER_SAMPLE  # 48000
        CHUNK_DURATION_MS = 100
        CHUNK_SIZE = int(BYTES_PER_SEC * CHUNK_DURATION_MS / 1000)  # 4800 bytes
        MAX_CHUNK_BYTES = 900_000  # stay well under 1MB limit

        event_id = str(uuid.uuid4())
        try:
            ws = self._ws_pool.get(ws_url)
            if not ws:
                ws = connect(ws_url)
                if not self._wait_for_lite_connected(ws):
                    try:
                        ws.close()
                    except Exception:
                        pass
                    return False
                self._ws_pool[ws_url] = ws

            offset = 0
            total = len(pcm_audio)
            chunk_index = 0
            while offset < total:
                chunk_end = min(offset + min(CHUNK_SIZE, MAX_CHUNK_BYTES), total)
                chunk = pcm_audio[offset:chunk_end]
                speak_msg = {
                    "type": "agent.speak",
                    "event_id": f"{event_id}-{chunk_index}",
                    "audio": base64.b64encode(chunk).decode("ascii"),
                }
                ws.send(json.dumps(speak_msg))
                offset = chunk_end
                chunk_index += 1

                # Pace to real time: sleep for the duration of this chunk
                if offset < total:
                    chunk_duration_sec = len(chunk) / BYTES_PER_SEC
                    time.sleep(chunk_duration_sec)

            # Signal end of audio
            end_msg = {
                "type": "agent.speak_end",
                "event_id": event_id,
            }
            ws.send(json.dumps(end_msg))
            return True
        except Exception:
            self._ws_pool.pop(ws_url, None)
            return False


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
