import time

from app.core.config import ELEVENLABS_API_KEY, ELEVENLABS_TTS_LANGUAGE, ELEVENLABS_TTS_MODEL, ELEVENLABS_TTS_VOICE_ID, TTS_LANGUAGE, TTS_PROVIDER
from app.schemas.dtos import (
    SpeechToTextEventDTO,
    TextToSpeechRequestDTO,
    TextToSpeechResultDTO,
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
        self.tts_provider = tts_provider or get_text_to_speech_provider()
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
        avatar_active = self._get_avatar_active()
        output_format = "pcm_24000" if avatar_active else "mp3_22050_32"
        try:
            tts = self.tts_provider.synthesize(TextToSpeechRequestDTO(
                text=text,
                language=TTS_LANGUAGE,
                outputFormat=output_format
            ))
            if avatar_active and getattr(tts, "pcmAudioBytes", None):
                from app.services.live_avatar_service import send_avatar_audio
                import threading
                # Stream audio to avatar in background thread so the HTTP
                # response returns immediately. send_audio now sleeps for
                # real-time pacing which would otherwise block the response.
                pcm_bytes = tts.pcmAudioBytes
                session_copy = self.session
                state_copy = self.state
                def _bg_send():
                    send_avatar_audio(session_copy, state_copy, pcm_bytes)
                threading.Thread(target=_bg_send, daemon=True).start()
        except TextToSpeechError:
            raise
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
        tts, avatar_active = self._process_tts_and_avatar(result.assistantText)

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
            avatarSessionActive=avatar_active,
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
