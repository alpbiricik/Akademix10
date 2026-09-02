from typing import AsyncIterator

from app.schemas.dtos import SpeechToTextEventDTO
from app.services.speech_to_text_provider import stt_metadata


class MockSpeechToTextProvider:
    provider_name = "mock"

    def __init__(self, transcript: str = "Teslim tarihini anliyorum ve birlikte bir takip plani yapalim.", model: str = "mock-stt-v1", language: str = "tr") -> None:
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
            yield SpeechToTextEventDTO(
                type="partial_transcript",
                transcript=self.transcript[: max(10, len(self.transcript) // 2)],
                metadata=stt_metadata(self.provider_name, self.model, self.language, confidence=0.9, first_partial_ms=12),
            )
            break
        if saw_audio:
            yield SpeechToTextEventDTO(
                type="final_transcript",
                transcript=self.transcript,
                isFinal=True,
                speechFinal=True,
                metadata=stt_metadata(self.provider_name, self.model, self.language, confidence=0.94, first_partial_ms=12, final_transcript_ms=35),
            )
            yield SpeechToTextEventDTO(
                type="utterance_end",
                metadata=stt_metadata(self.provider_name, self.model, self.language, utterance_end_ms=36),
            )
        else:
            yield SpeechToTextEventDTO(
                type="error",
                metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="no_audio"),
            )
        yield SpeechToTextEventDTO(type="stream_closed", metadata=metadata)
