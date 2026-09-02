import base64
import time

from app.schemas.dtos import TextToSpeechMetadataDTO, TextToSpeechRequestDTO, TextToSpeechResultDTO
from app.services.text_to_speech_provider import TextToSpeechError


class MockTextToSpeechProvider:
    provider_name = "mock"
    model = "mock-tts-v1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        started = time.perf_counter()
        if self.fail:
            raise TextToSpeechError("Mock TTS failure.")
        payload = base64.b64encode(b"MOCK_AUDIO").decode("ascii")
        elapsed = int((time.perf_counter() - started) * 1000)
        return TextToSpeechResultDTO(
            audioPayloadBase64=payload,
            contentType="audio/mock",
            textFallback=request.text,
            metadata=TextToSpeechMetadataDTO(
                provider=self.provider_name,
                model=self.model,
                voice=request.voice,
                language=request.language,
                characterCount=len(request.text),
                firstAudioMs=elapsed,
                synthesisCompleteMs=elapsed,
            ),
        )


def text_fallback_result(text: str, language: str = "tr", error_code: str = "tts_unavailable") -> TextToSpeechResultDTO:
    return TextToSpeechResultDTO(
        textFallback=text,
        metadata=TextToSpeechMetadataDTO(
            provider="fallback",
            model="text-only",
            voice="none",
            language=language,
            characterCount=len(text),
            errorCode=error_code,
        ),
    )
