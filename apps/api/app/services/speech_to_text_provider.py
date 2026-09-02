from typing import AsyncIterator, Protocol

from app.schemas.dtos import SpeechToTextEventDTO, SpeechToTextMetadataDTO


class SpeechToTextProvider(Protocol):
    provider_name: str
    model: str
    language: str

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[SpeechToTextEventDTO]:
        ...


def stt_metadata(
    provider: str,
    model: str,
    language: str,
    confidence: float | None = None,
    first_partial_ms: int | None = None,
    final_transcript_ms: int | None = None,
    utterance_end_ms: int | None = None,
    error_code: str | None = None,
) -> SpeechToTextMetadataDTO:
    return SpeechToTextMetadataDTO(
        provider=provider,
        model=model,
        language=language,
        confidence=confidence,
        firstPartialMs=first_partial_ms,
        finalTranscriptMs=final_transcript_ms,
        utteranceEndMs=utterance_end_ms,
        errorCode=error_code,
    )
