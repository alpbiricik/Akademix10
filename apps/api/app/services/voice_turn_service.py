import time

from app.core.config import ELEVENLABS_API_KEY, ELEVENLABS_TTS_LANGUAGE, ELEVENLABS_TTS_MODEL, ELEVENLABS_TTS_VOICE_ID, TTS_LANGUAGE, TTS_PROVIDER
from app.schemas.dtos import (
    SpeechToTextEventDTO,
    TextToSpeechRequestDTO,
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
from app.services.mock_text_to_speech_provider import MockTextToSpeechProvider, text_fallback_result
from app.services.text_to_speech_provider import TextToSpeechError, TextToSpeechProvider
from app.services.elevenlabs_tts_provider import ElevenLabsTextToSpeechProvider


class VoiceTurnError(Exception):
    code = "voice_turn_error"


class DuplicateFinalTranscriptError(VoiceTurnError):
    code = "duplicate_final_transcript"


class EmptyTranscriptError(VoiceTurnError):
    code = "empty_transcript"


class UnavailableTextToSpeechProvider:
    provider_name = "unavailable"

    def __init__(self, error_code: str) -> None:
        self.error_code = error_code

    def synthesize(self, request: TextToSpeechRequestDTO):
        raise TextToSpeechError(self.error_code)


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
        self.tts_provider = tts_provider or get_text_to_speech_provider()
        self.cache = cache
        self._final_processed = False
        self._stream_started_at = time.perf_counter()
        self.partial_event_count = 0
        self.final_event_count = 0

    def start_opening(self) -> VoiceOpeningResultDTO:
        self.ensure_accepting_turn()
        started = time.perf_counter()
        result = conversation_service.start_training_conversation(
            self.session,
            self.state,
            provider=self.conversation_provider,
            cache=self.cache,
        )
        conversation_ms = int((time.perf_counter() - started) * 1000)
        try:
            tts = self.tts_provider.synthesize(TextToSpeechRequestDTO(text=result.assistantText, language=TTS_LANGUAGE))
        except TextToSpeechError:
            tts = text_fallback_result(result.assistantText, language=TTS_LANGUAGE, error_code="tts_synthesis_failed")
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
        )

    def handle_partial(self, event: SpeechToTextEventDTO) -> None:
        if event.type == "partial_transcript":
            self.partial_event_count += 1

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
        try:
            tts = self.tts_provider.synthesize(TextToSpeechRequestDTO(text=result.assistantText, language=TTS_LANGUAGE))
        except TextToSpeechError:
            tts = text_fallback_result(result.assistantText, language=TTS_LANGUAGE, error_code="tts_synthesis_failed")
        metrics = VoiceTurnMetricsDTO(
            streamStartedAt=None,
            firstPartialMs=event.metadata.firstPartialMs,
            finalTranscriptMs=event.metadata.finalTranscriptMs,
            utteranceEndMs=event.metadata.utteranceEndMs,
            conversationResponseMs=conversation_ms,
            firstAudioMs=tts.metadata.firstAudioMs,
            synthesisCompleteMs=tts.metadata.synthesisCompleteMs,
            speechEndToFirstAudioMs=tts.metadata.firstAudioMs,
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
        )

    def ensure_accepting_turn(self) -> None:
        if self.state.id in self.session.completedStateIds:
            raise ConversationStateError("Conversation is already complete for this state.")


def get_text_to_speech_provider() -> TextToSpeechProvider:
    if TTS_PROVIDER == "elevenlabs":
        try:
            return ElevenLabsTextToSpeechProvider(
                api_key=ELEVENLABS_API_KEY,
                voice_id=ELEVENLABS_TTS_VOICE_ID,
                model=ELEVENLABS_TTS_MODEL,
                language=ELEVENLABS_TTS_LANGUAGE,
            )
        except TextToSpeechError as error:
            return UnavailableTextToSpeechProvider(getattr(error, "code", "tts_unavailable"))
    return MockTextToSpeechProvider()
