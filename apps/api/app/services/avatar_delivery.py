"""Short-lived delivery status; audio exists in RAM only for failure recovery."""
import base64
import io
import threading
import uuid
import wave
import time

from app.services.conversation_cache import InMemoryConversationCache

deliveries = InMemoryConversationCache()
DELIVERY_TTL_SECONDS = 120


def _key(session_id: str, delivery_id: str) -> str:
    return f"delivery:{session_id}:{delivery_id}"


def start_delivery(session, state, pcm_audio: bytes, generation=None) -> str | None:
    delivery_id = str(uuid.uuid4())
    key = _key(session.id, delivery_id)
    cancelled = threading.Event()
    with _jobs_lock:
        if generation is not None and generation != delivery_generation(session.id, state.id):
            return None
        if len(_jobs) >= MAX_ACTIVE_DELIVERIES:
            deliveries.put(key, {"status": "text_only", "errorCode": "tts_capacity"}, DELIVERY_TTL_SECONDS)
            return delivery_id
        _jobs[key] = (session.id, state.id, cancelled)
        deliveries.put(key, {"status": "sending"}, DELIVERY_TTL_SECONDS)
    def send():
        from app.services.live_avatar_service import send_avatar_audio
        from app.services.voice_poc_metrics import voice_poc_metrics
        started = time.perf_counter()
        partial = False
        try:
            success = send_avatar_audio(session, state, pcm_audio, cancel_event=cancelled)
        except Exception as error:
            from app.services.live_avatar_provider import LiveAvatarPartialAudioError
            partial = isinstance(error, LiveAvatarPartialAudioError)
            success = False
        if success:
            result = {"status": "completed"}
            voice_poc_metrics.record(session.id, state.id, "avatar_delivery", latency_ms=(time.perf_counter() - started) * 1000)
        elif partial or cancelled.is_set():
            result = {"status": "text_only", "errorCode": "avatar_partial_audio"}
        else:
            voice_poc_metrics.record(session.id, state.id, "fallback")
            # Wrap the same PCM in a WAV header for browser playback. This
            # doesn't write a file or repeat the TTS provider request.
            output = io.BytesIO()
            with wave.open(output, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(24000)
                audio.writeframes(pcm_audio)
            result = {"status": "fallback", "contentType": "audio/wav",
                      "audioPayloadBase64": base64.b64encode(output.getvalue()).decode("ascii")}
        with _jobs_lock:
            deliveries.put(key, {"status": "cancelled"} if cancelled.is_set() else result, DELIVERY_TTL_SECONDS)
            _jobs.pop(key, None)
    threading.Thread(target=send, daemon=True, name="avatar-delivery").start()
    return delivery_id


def delivery_status(session_id: str, delivery_id: str) -> dict:
    return deliveries.get(_key(session_id, delivery_id)) or {"status": "expired"}


_generations = InMemoryConversationCache()
_jobs_lock = threading.RLock()


def delivery_generation(session_id, state_id):
    with _jobs_lock:
        return (_generations.get(f"session:{session_id}"), _generations.get(f"state:{session_id}:{state_id}"))

MAX_ACTIVE_DELIVERIES = 16
_jobs: dict[str, tuple[str, str, threading.Event]] = {}


def cancel_deliveries(session_id: str, state_id: str | None = None) -> None:
    from app.services.voice_poc_metrics import voice_poc_metrics
    with _jobs_lock:
        generation_key = f"state:{session_id}:{state_id}" if state_id is not None else f"session:{session_id}"
        _generations.put(generation_key, str(uuid.uuid4()), 3600)
        for key, (owner, state, event) in list(_jobs.items()):
            if owner == session_id and (state_id is None or state == state_id):
                if not event.is_set():
                    voice_poc_metrics.record(session_id, state, "cancel")
                event.set()
                deliveries.put(key, {"status": "cancelled"}, DELIVERY_TTL_SECONDS)


def start_stream_delivery(session, state, provider, request, generation=None) -> str | None:
    from app.services.text_to_speech_provider import TextToSpeechError
    from app.services.voice_poc_metrics import voice_poc_metrics
    delivery_id = str(uuid.uuid4())
    key = _key(session.id, delivery_id)
    cancelled = threading.Event()
    with _jobs_lock:
        if generation is not None and generation != delivery_generation(session.id, state.id):
            return None
        for owner, state_id, event in _jobs.values():
            if owner == session.id and state_id == state.id:
                event.set()
        if len(_jobs) >= MAX_ACTIVE_DELIVERIES:
            deliveries.put(key, {"status": "text_only", "errorCode": "tts_capacity"}, DELIVERY_TTL_SECONDS)
            return delivery_id
        _jobs[key] = (session.id, state.id, cancelled)
        deliveries.put(key, {"status": "sending"}, DELIVERY_TTL_SECONDS)

    def send():
        from app.services.live_avatar_service import send_avatar_audio_stream
        started = time.perf_counter()
        first = True
        def chunks():
            nonlocal first
            for chunk in provider.stream(request, cancelled):
                if first:
                    first = False
                    voice_poc_metrics.record(session.id, state.id, "tts", characters=len(request.text), first_audio_ms=(time.perf_counter() - started) * 1000)
                yield chunk
        stream = chunks()
        try:
            success = send_avatar_audio_stream(session, state, stream, cancelled)
            result = {"status": "completed"} if success else {"status": "text_only", "errorCode": "avatar_delivery_failed"}
            if success:
                voice_poc_metrics.record(session.id, state.id, "avatar_delivery", latency_ms=(time.perf_counter() - started) * 1000)
        except Exception as error:
            result = {"status": "text_only", "errorCode": error.code if isinstance(error, TextToSpeechError) else "avatar_delivery_failed"}
        finally:
            stream.close()
        with _jobs_lock:
            if cancelled.is_set():
                result = {"status": "cancelled"}
            deliveries.put(key, result, DELIVERY_TTL_SECONDS)
            _jobs.pop(key, None)
    threading.Thread(target=send, daemon=True, name="avatar-stream-delivery").start()
    return delivery_id
