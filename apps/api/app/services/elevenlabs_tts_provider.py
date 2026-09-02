import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from app.schemas.dtos import TextToSpeechMetadataDTO, TextToSpeechRequestDTO, TextToSpeechResultDTO
from app.services.text_to_speech_provider import TextToSpeechError


class ElevenLabsTTSConfigurationError(TextToSpeechError):
    code = "elevenlabs_tts_not_configured"


class ElevenLabsTextToSpeechProvider:
    provider_name = "elevenlabs"

    def __init__(self, api_key: str, voice_id: str, model: str = "eleven_flash_v2_5", language: str = "tr") -> None:
        if not api_key:
            raise ElevenLabsTTSConfigurationError("ElevenLabs TTS requires a server-side API key.")
        if not voice_id:
            raise ElevenLabsTTSConfigurationError("ElevenLabs TTS requires ELEVENLABS_TTS_VOICE_ID.")
        self._api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.language = language

    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        started = time.perf_counter()
        first_audio_ms: int | None = None
        chunks: list[bytes] = []
        query = urllib.parse.urlencode({"output_format": "mp3_22050_32", "language_code": self.language})
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{urllib.parse.quote(self.voice_id)}/stream?{query}"
        http_request = urllib.request.Request(
            url,
            data=json.dumps({"text": request.text, "model_id": self.model}).encode("utf-8"),
            headers={"Content-Type": "application/json", "xi-api-key": self._api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=30) as response:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    if first_audio_ms is None:
                        first_audio_ms = int((time.perf_counter() - started) * 1000)
                    chunks.append(chunk)
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise TextToSpeechError("ElevenLabs TTS request failed.") from error
        total_ms = int((time.perf_counter() - started) * 1000)
        if not chunks:
            raise TextToSpeechError("ElevenLabs TTS returned no audio.")
        return TextToSpeechResultDTO(
            audioPayloadBase64=base64.b64encode(b"".join(chunks)).decode("ascii"),
            contentType="audio/mpeg",
            textFallback=request.text,
            metadata=TextToSpeechMetadataDTO(
                provider=self.provider_name,
                model=self.model,
                voice=self.voice_id,
                language=self.language,
                characterCount=len(request.text),
                firstAudioMs=first_audio_ms,
                synthesisCompleteMs=total_ms,
            ),
        )
