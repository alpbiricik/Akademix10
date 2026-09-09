"""Prepare opening speech before billed avatar startup; bounded, ephemeral RAM only."""
import threading
import time
import uuid

from app.core.config import TTS_LANGUAGE
from app.schemas.dtos import TextToSpeechRequestDTO, TextToSpeechResultDTO, TextToSpeechMetadataDTO, VoiceOpeningResultDTO, VoiceTurnMetricsDTO
from app.services import conversation_service
from app.services.avatar_delivery import delivery_generation, start_delivery
from app.services.conversation_cache import conversation_cache
from app.services.conversation_errors import ConversationStateError
from app.services.live_avatar_service import avatar_session_store, verify_avatar_state
from app.services.text_to_speech_provider import TextToSpeechError
from app.services.voice_turn_service import get_text_to_speech_provider
from app.services.voice_poc_metrics import voice_poc_metrics

TTL_SECONDS = 120
MAX_ENTRIES = 16
MAX_ENTRY_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
_lock = threading.RLock()
_stripes = tuple(threading.RLock() for _ in range(32))
_entries = {}


def _expire(key, entry):
    with _lock:
        if _entries.get(key) is entry:
            _entries.pop(key, None)
            entry["timer"].cancel()


def cancel_prepared_openings(session_id, state_id=None):
    with _lock:
        for key, entry in list(_entries.items()):
            if key[0] == session_id and (state_id is None or key[1] == state_id):
                _expire(key, entry)


def _check_generation(session, state, entry):
    if entry["generation"] != delivery_generation(session.id, state.id) or time.monotonic() >= entry["expires"]:
        raise ConversationStateError("Prepared opening expired or cancelled. Prepare it again.")


def _verify_current(session, state):
    verify_avatar_state(session, state)
    if session.currentStateId != state.id or state.id in session.completedStateIds or getattr(session, "completedAt", None):
        raise ConversationStateError("Opening is only available for the current unfinished state.")


def prepare_opening(session, state, conversation_provider=None, tts_provider=None, cache=conversation_cache):
    _verify_current(session, state)
    key = (session.id, state.id)
    with _stripes[hash(key) % len(_stripes)]:
        generation = delivery_generation(*key)
        with _lock:
            existing = _entries.get(key)
            if existing and existing["generation"] == generation and time.monotonic() < existing["expires"]:
                return dict(existing["public"])
            if existing:
                _expire(key, existing)
            if len(_entries) >= MAX_ENTRIES:
                return {"preparedOpeningId": None, "assistantText": "", "errorCode": "tts_capacity"}
            entry = {"generation": generation, "expires": time.monotonic() + TTL_SECONDS, "pcm": b"", "public": {}}
            timer = threading.Timer(TTL_SECONDS, _expire, args=(key, entry))
            timer.daemon = True
            entry["timer"] = timer
            _entries[key] = entry
            timer.start()
        try:
            started = time.perf_counter()
            result = conversation_service.start_training_conversation(session, state, provider=conversation_provider, cache=cache)
            conversation_ms = int((time.perf_counter() - started) * 1000)
            voice_poc_metrics.record(session.id, state.id, "conversation", latency_ms=conversation_ms,
                input_tokens=result.providerMetadata.inputTokens or 0, output_tokens=result.providerMetadata.outputTokens or 0)
            _check_generation(session, state, entry)
            try:
                provider = tts_provider or get_text_to_speech_provider()
                request = TextToSpeechRequestDTO(text=result.assistantText, language=TTS_LANGUAGE, outputFormat="pcm_24000")
                if callable(getattr(provider, "stream", None)):
                    audio = bytearray()
                    first_audio_ms = None
                    synthesis_started = time.perf_counter()
                    stream = provider.stream(request)
                    try:
                        for chunk in stream:
                            _check_generation(session, state, entry)
                            if first_audio_ms is None:
                                first_audio_ms = int((time.perf_counter() - synthesis_started) * 1000)
                            if len(audio) + len(chunk) > MAX_ENTRY_BYTES:
                                raise TextToSpeechError("Opening audio exceeds preparation capacity.", code="tts_capacity")
                            audio.extend(chunk)
                    finally:
                        if callable(getattr(stream, "close", None)):
                            stream.close()
                    tts = TextToSpeechResultDTO(pcmAudioBytes=bytes(audio), textFallback=result.assistantText,
                        metadata=TextToSpeechMetadataDTO(provider=provider.provider_name, model=getattr(provider, "model", ""), voice=getattr(provider, "voice_id", ""), language=TTS_LANGUAGE,
                            characterCount=len(result.assistantText), firstAudioMs=first_audio_ms, synthesisCompleteMs=int((time.perf_counter() - synthesis_started) * 1000)))
                else:
                    tts = provider.synthesize(request)
                pcm = tts.pcmAudioBytes or b""
                if not pcm:
                    raise TextToSpeechError("Speech unavailable.", code="tts_empty_audio")
                if len(pcm) > MAX_ENTRY_BYTES:
                    raise TextToSpeechError("Opening audio exceeds preparation capacity.", code="tts_capacity")
                _check_generation(session, state, entry)
                voice_poc_metrics.record(session.id, state.id, "tts", characters=tts.metadata.characterCount,
                    **({"first_audio_ms": tts.metadata.firstAudioMs} if tts.metadata.firstAudioMs is not None else {}))
                with _lock:
                    if _entries.get(key) is not entry:
                        raise ConversationStateError("Prepared opening was cancelled.")
                    if sum(len(item["pcm"]) for item in _entries.values()) + len(pcm) > MAX_TOTAL_BYTES:
                        raise TextToSpeechError("Opening preparation capacity reached.", code="tts_capacity")
                    entry.update(pcm=pcm, tts=tts.model_copy(update={"pcmAudioBytes": None}), result=result, conversation_ms=conversation_ms,
                        public={"preparedOpeningId": str(uuid.uuid4()), "assistantText": result.assistantText})
            except TextToSpeechError as error:
                voice_poc_metrics.record(session.id, state.id, "fallback")
                entry["public"] = {"preparedOpeningId": None, "assistantText": result.assistantText, "errorCode": error.code if error.code != "tts_error" else "tts_synthesis_failed"}
            return dict(entry["public"])
        except Exception:
            _expire(key, entry)
            raise


def consume_prepared_opening(session, state, prepared_id):
    _verify_current(session, state)
    key = (session.id, state.id)
    with _stripes[hash(key) % len(_stripes)]:
        with _lock:
            entry = _entries.get(key)
            if not entry or not prepared_id or entry["public"].get("preparedOpeningId") != prepared_id:
                raise ConversationStateError("Prepared opening unavailable. Prepare it again.")
            _check_generation(session, state, entry)
            if "consumed" in entry:
                return entry["consumed"].model_copy(deep=True)
            if not avatar_session_store.get_token(session.id, state.id):
                raise ConversationStateError("Start the avatar before consuming prepared speech.")
            delivery_id = start_delivery(session, state, entry["pcm"], generation=entry["generation"])
            if not delivery_id:
                raise ConversationStateError("Prepared opening was cancelled.")
            result, tts = entry["result"], entry["tts"]
            response = VoiceOpeningResultDTO(stateId=state.id, assistantText=result.assistantText, conversationComplete=False,
                conversationProviderMetadata=result.providerMetadata, tts=tts,
                metrics=VoiceTurnMetricsDTO(conversationResponseMs=entry["conversation_ms"], firstAudioMs=tts.metadata.firstAudioMs, synthesisCompleteMs=tts.metadata.synthesisCompleteMs),
                avatarSessionActive=True, avatarDeliveryId=delivery_id)
            entry["consumed"] = response
            entry["pcm"] = b""
            return response.model_copy(deep=True)
