import time
from app.core import config

from app.core.config import ELEVENLABS_API_KEY, ELEVENLABS_TTS_LANGUAGE, ELEVENLABS_TTS_MODEL, ELEVENLABS_TTS_VOICE_ID, TTS_LANGUAGE, TTS_PROVIDER
from app.schemas.dtos import (
    SpeechToTextEventDTO,
    TextToSpeechRequestDTO,
    TextToSpeechResultDTO,
    TextToSpeechMetadataDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    VoiceTurnMetricsDTO,
    VoiceOpeningResultDTO,
    VoiceTurnResultDTO,
)
from app.services.conversation_cache import InMemoryConversationCache, conversation_cache
from app.services.conversation_errors import ConversationStateError
from app.services.conversation_provider import ConversationProvider
from app.services import conversation_service
from app.services.text_to_speech_provider import TextToSpeechError, TextToSpeechProvider
from app.services.elevenlabs_tts_provider import ElevenLabsTextToSpeechProvider
from app.services.voice_poc_metrics import voice_poc_metrics


class VoiceTurnError(Exception):
    code = "voice_turn_error"


class DuplicateFinalTranscriptError(VoiceTurnError):
    code = "duplicate_final_transcript"


class EmptyTranscriptError(VoiceTurnError):
    code = "empty_transcript"


class VoiceTurnOrchestrator:
    def __init__(
        self,
        session: TrainingSessionDTO,
        state: TrainingStateDTO,
        conversation_provider: ConversationProvider | None = None,
        tts_provider: TextToSpeechProvider | None = None,
        cache: InMemoryConversationCache = conversation_cache,
    ) -> None:
        self.session = session
        self.state = state
        self.conversation_provider = conversation_provider
        self.tts_provider = tts_provider
        self.avatar_delivery_id = None
        from app.services.avatar_delivery import delivery_generation
        self.delivery_generation = delivery_generation(session.id, state.id)
        self.cache = cache
        from app.services.live_avatar_service import avatar_session_store
        self.avatar_store = avatar_session_store
        self._final_processed = False
        self._stream_started_at = time.perf_counter()
        self.partial_event_count = 0
        self.final_event_count = 0

    def _get_avatar_active(self) -> bool:
        entry = self.avatar_store.get(self.session.id, self.state.id)
        return bool(entry and "tokenResponse" in entry)

    def _process_tts_and_avatar(self, text: str) -> tuple[TextToSpeechResultDTO, bool]:
        from app.services.avatar_delivery import delivery_generation
        if self.delivery_generation != delivery_generation(self.session.id, self.state.id):
            return TextToSpeechResultDTO(textFallback=text, metadata=TextToSpeechMetadataDTO(provider=TTS_PROVIDER, model=ELEVENLABS_TTS_MODEL, voice="", language=TTS_LANGUAGE, errorCode="tts_cancelled")), False
        avatar_active = self._get_avatar_active()
        output_format = "pcm_24000" if avatar_active else "mp3_22050_32"
        try:
            provider = self.tts_provider or get_text_to_speech_provider()
            if getattr(config, "VOICE_STREAMING_ENABLED", False) and avatar_active and callable(getattr(provider, "stream", None)):
                from app.services.avatar_delivery import start_stream_delivery
                self.avatar_delivery_id = start_stream_delivery(self.session, self.state, provider, TextToSpeechRequestDTO(text=text, language=TTS_LANGUAGE, outputFormat="pcm_24000"), generation=self.delivery_generation)
                return TextToSpeechResultDTO(textFallback=text, metadata=TextToSpeechMetadataDTO(provider=provider.provider_name, model=getattr(provider, "model", ""), voice="", language=TTS_LANGUAGE, characterCount=len(text))), self.avatar_delivery_id is not None
            tts = provider.synthesize(TextToSpeechRequestDTO(
                text=text,
                language=TTS_LANGUAGE,
                outputFormat=output_format
            ))
            voice_poc_metrics.record(self.session.id, self.state.id, "tts", characters=tts.metadata.characterCount,
                                     **({"first_audio_ms": tts.metadata.firstAudioMs} if tts.metadata.firstAudioMs is not None else {}))
            if avatar_active and getattr(tts, "pcmAudioBytes", None):
                from app.services.avatar_delivery import start_delivery
                self.avatar_delivery_id = start_delivery(self.session, self.state, tts.pcmAudioBytes, generation=self.delivery_generation)
        except TextToSpeechError as error:
            voice_poc_metrics.record(self.session.id, self.state.id, "fallback")
            tts = TextToSpeechResultDTO(textFallback=text, metadata=TextToSpeechMetadataDTO(
                provider=TTS_PROVIDER, model=ELEVENLABS_TTS_MODEL, voice="", language=TTS_LANGUAGE,
                errorCode=error.code if error.code != "tts_error" else "tts_synthesis_failed"))
            avatar_active = False
        return tts, avatar_active

    def start_opening(self) -> VoiceOpeningResultDTO:
        started = time.perf_counter()
        result = conversation_service.start_training_conversation(
            self.session,
            self.state,
            provider=self.conversation_provider,
            cache=self.cache,
        )

        conversation_ms = int((time.perf_counter() - started) * 1000)
        voice_poc_metrics.record(self.session.id, self.state.id, "conversation", latency_ms=conversation_ms,
                                 input_tokens=result.providerMetadata.inputTokens or 0, output_tokens=result.providerMetadata.outputTokens or 0)
        tts, avatar_active = self._process_tts_and_avatar(result.assistantText)

        return VoiceOpeningResultDTO(
            stateId=self.state.id,
            assistantText=result.assistantText,
            conversationComplete=False,
            conversationProviderMetadata=result.providerMetadata,
            tts=tts,
            metrics=VoiceTurnMetricsDTO(
                conversationResponseMs=conversation_ms,
                firstAudioMs=tts.metadata.firstAudioMs,
                synthesisCompleteMs=tts.metadata.synthesisCompleteMs,
            ),
            avatarSessionActive=avatar_active,
            avatarDeliveryId=self.avatar_delivery_id,
        )

    def handle_partial(self, event: SpeechToTextEventDTO) -> None:
        if event.type == "partial_transcript":
            self.partial_event_count += 1
            if self.partial_event_count == 1 and event.metadata.firstPartialMs is not None:
                voice_poc_metrics.record(self.session.id, self.state.id, "stt_partial", latency_ms=event.metadata.firstPartialMs)

    def handle_final(self, event: SpeechToTextEventDTO) -> VoiceTurnResultDTO | None:
        if event.type not in {"final_transcript", "committed_transcript"}:
            return None
        if self._final_processed:
            return None
        transcript = (event.transcript or "").strip()
        if not transcript:
            raise EmptyTranscriptError("Final transcript was empty.")
        self._final_processed = True
        self.final_event_count += 1
        started = time.perf_counter()
        result, turn_number, complete, guardrail = conversation_service.continue_training_conversation(
            self.session,
            self.state,
            transcript,
            provider=self.conversation_provider,
            cache=self.cache,
        )
        conversation_ms = int((time.perf_counter() - started) * 1000)
        voice_poc_metrics.record(self.session.id, self.state.id, "conversation", latency_ms=conversation_ms,
                                 input_tokens=result.providerMetadata.inputTokens or 0, output_tokens=result.providerMetadata.outputTokens or 0)
        tts, avatar_active = self._process_tts_and_avatar(result.assistantText)

        metrics = VoiceTurnMetricsDTO(
            streamStartedAt=None,
            firstPartialMs=event.metadata.firstPartialMs,
            finalTranscriptMs=event.metadata.finalTranscriptMs,
            utteranceEndMs=event.metadata.utteranceEndMs,
            conversationResponseMs=conversation_ms,
            firstAudioMs=tts.metadata.firstAudioMs,
            synthesisCompleteMs=tts.metadata.synthesisCompleteMs,
            speechEndToFirstAudioMs=conversation_ms + tts.metadata.firstAudioMs if tts.metadata.firstAudioMs is not None else None,
        )
        return VoiceTurnResultDTO(
            stateId=self.state.id,
            turnNumber=turn_number,
            assistantText=result.assistantText,
            action=result.action,
            conversationComplete=complete,
            guardrail=guardrail,
            conversationProviderMetadata=result.providerMetadata,
            sttMetadata=event.metadata,
            tts=tts,
            metrics=metrics,
            avatarSessionActive=avatar_active,
            avatarDeliveryId=self.avatar_delivery_id,
        )

    def ensure_accepting_turn(self) -> None:
        if self.state.id in self.session.completedStateIds:
            raise ConversationStateError("Conversation is already complete for this state.")


def get_text_to_speech_provider() -> TextToSpeechProvider:
    if TTS_PROVIDER and TTS_PROVIDER != "elevenlabs":
        raise TextToSpeechError("TTS_PROVIDER must be elevenlabs.")
    return ElevenLabsTextToSpeechProvider(
        api_key=ELEVENLABS_API_KEY,
        voice_id=ELEVENLABS_TTS_VOICE_ID,
        model=ELEVENLABS_TTS_MODEL,
        language=ELEVENLABS_TTS_LANGUAGE,
    )
