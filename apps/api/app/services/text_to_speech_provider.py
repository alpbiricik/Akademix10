from typing import Protocol

from app.schemas.dtos import TextToSpeechRequestDTO, TextToSpeechResultDTO


class TextToSpeechProvider(Protocol):
    provider_name: str

    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        ...


class TextToSpeechError(Exception):
    code = "tts_error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
