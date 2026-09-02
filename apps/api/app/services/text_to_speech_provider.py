from typing import Protocol

from app.schemas.dtos import TextToSpeechRequestDTO, TextToSpeechResultDTO


class TextToSpeechProvider(Protocol):
    provider_name: str

    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        ...


class TextToSpeechError(Exception):
    code = "tts_error"
