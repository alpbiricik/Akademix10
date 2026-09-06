import base64
import time
from hashlib import sha256
from typing import AsyncIterator

from app.schemas.dtos import (
    ConversationRequestDTO,
    ConversationResultDTO,
    DimensionScoreDTO,
    GuardrailFlagDTO,
    LiveAvatarSessionActionResponseDTO,
    LiveAvatarSessionTokenResponseDTO,
    ProviderMetadataDTO,
    ProviderRequestDTO,
    ProviderScoringResponseDTO,
    SpeechToTextEventDTO,
    TextToSpeechMetadataDTO,
    TextToSpeechRequestDTO,
    TextToSpeechResultDTO,
)
from app.services.speech_to_text_provider import stt_metadata
from app.services.text_to_speech_provider import TextToSpeechError


class DeterministicScoringProvider:
    provider_name = "mock"

    def score(self, request: ProviderRequestDTO) -> ProviderScoringResponseDTO:
        normalized = " ".join(request.answerText.lower().split())
        seed = int(sha256(f"{request.sessionId}|{request.stateId}|{normalized}".encode("utf-8")).hexdigest()[:8], 16)
        scores = []
        for index, dimension in enumerate(request.rubric.dimensions):
            score = max(dimension.minScore, min(dimension.maxScore, 70 + ((seed >> (index * 4)) & 0xF) % 8))
            scores.append(DimensionScoreDTO(dimensionId=dimension.id, name=dimension.name, score=score, rationale=f"Test fake score for {dimension.name}."))
        flags = [GuardrailFlagDTO(code="prompt_injection_pattern", message="Instruction-like content.", severity="warning")] if "system prompt" in normalized else []
        return ProviderScoringResponseDTO(
            dimensionScores=scores,
            conciseLearnerFeedback="Deterministic test feedback.",
            strengths=["Acknowledges the scenario."],
            improvementAreas=["Add one sharper discovery question."],
            recommendedNextAction="complete_state",
            guardrailFlags=flags,
            providerMetadata=ProviderMetadataDTO(provider=self.provider_name, model="deterministic-test-fake-v1", attemptCount=1, fallbackUsed=False),
        )


class DeterministicConversationProvider:
    provider_name = "mock"
    model = "mock-conversation-v1"

    def continue_conversation(self, request: ConversationRequestDTO) -> ConversationResultDTO:
        should_complete = request.turnNumber >= request.maxTurns or (
            request.turnNumber >= request.minTurns and any(word in request.sanitizedLearnerTurn.lower() for word in {"next", "commit", "meeting", "plan", "takip"})
        )
        return ConversationResultDTO(
            assistantText="Anladim. Net bir sonraki adim sundun; bu gorusmeyi kapatabiliriz." if should_complete else "Bunu duyuyorum. Bir sonraki cumleni nasil kurardin?",
            action="complete" if should_complete else "continue",
            reasonCode="test_fake_turn_boundary",
            providerMetadata=ProviderMetadataDTO(provider=self.provider_name, model=self.model),
        )


class DeterministicSpeechToTextProvider:
    provider_name = "mock"

    def __init__(self, transcript: str = "Teslim tarihini anliyorum ve birlikte bir takip plani yapalim.", model: str = "test-stt-fake-v1", language: str = "tr") -> None:
        self.model = model
        self.language = language
        self.transcript = transcript

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[SpeechToTextEventDTO]:
        metadata = stt_metadata(self.provider_name, self.model, self.language)
        yield SpeechToTextEventDTO(type="stream_started", metadata=metadata)
        saw_audio = False
        async for chunk in audio_chunks:
            if not chunk:
                continue
            saw_audio = True
            yield SpeechToTextEventDTO(type="speech_started", metadata=metadata)
            yield SpeechToTextEventDTO(type="partial_transcript", transcript=self.transcript[:10], metadata=metadata)
            break
        if saw_audio:
            yield SpeechToTextEventDTO(type="final_transcript", transcript=self.transcript, isFinal=True, speechFinal=True, metadata=metadata)
            yield SpeechToTextEventDTO(type="utterance_end", metadata=metadata)
        else:
            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="no_audio"))
        yield SpeechToTextEventDTO(type="stream_closed", metadata=metadata)


class DeterministicTextToSpeechProvider:
    provider_name = "mock"
    model = "mock-tts-v1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        started = time.perf_counter()
        if self.fail:
            raise TextToSpeechError("Test fake TTS failure.")
        elapsed = int((time.perf_counter() - started) * 1000)
        return TextToSpeechResultDTO(
            audioPayloadBase64=base64.b64encode(b"TEST_FAKE_AUDIO").decode("ascii"),
            contentType="audio/test-fake",
            textFallback=request.text,
            metadata=TextToSpeechMetadataDTO(provider=self.provider_name, model=self.model, voice=request.voice, language=request.language, characterCount=len(request.text), firstAudioMs=elapsed, synthesisCompleteMs=elapsed),
        )


class DeterministicLiveAvatarProvider:
    provider_name = "mock"

    def __init__(self, avatar_id: str = "avatar-tr-1", voice_id: str = "voice-tr-1") -> None:
        self.avatar_id = avatar_id
        self.voice_id = voice_id

    def create_session_token(self, state_id: str) -> LiveAvatarSessionTokenResponseDTO:
        return LiveAvatarSessionTokenResponseDTO(
            provider=self.provider_name,
            sessionToken=f"test-avatar-token-{state_id}",
            avatarId=self.avatar_id,
            voiceId=self.voice_id,
            quality="medium",
            sessionTimeoutSec=600,
            metadata={"avatarSessionId": f"test-avatar-session-{state_id}", "livekitUrl": "wss://test.livekit.local", "livekitClientToken": "test-livekit-token"},
        )

    def stop_session(self, avatar_session_id: str) -> bool:
        return bool(avatar_session_id)

    def send_audio(self, ws_url: str, pcm_audio: bytes) -> bool:
        return bool(ws_url and pcm_audio)


def text_fallback_result(text: str, language: str = "tr", error_code: str = "tts_unavailable") -> TextToSpeechResultDTO:
    return TextToSpeechResultDTO(
        textFallback=text,
        metadata=TextToSpeechMetadataDTO(provider="fallback", model="text-only", voice="none", language=language, characterCount=len(text), errorCode=error_code),
    )
