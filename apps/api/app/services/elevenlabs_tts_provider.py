import base64
import http.client
import json
import time
import threading
import urllib.error
import urllib.parse
import urllib.request

from app.schemas.dtos import TextToSpeechMetadataDTO, TextToSpeechRequestDTO, TextToSpeechResultDTO
from app.services.text_to_speech_provider import TextToSpeechError


class ElevenLabsTTSConfigurationError(TextToSpeechError):
    code = "elevenlabs_tts_not_configured"


class ElevenLabsTextToSpeechProvider:
    provider_name = "elevenlabs"

    def __init__(self, api_key: str, voice_id: str = "", model: str = "eleven_flash_v2_5", language: str = "tr") -> None:
        if not api_key:
            raise ElevenLabsTTSConfigurationError("ElevenLabs TTS requires a server-side API key.")
        self._api_key = api_key
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.model = model or "eleven_flash_v2_5"
        self.language = language or "tr"


    def synthesize(self, request: TextToSpeechRequestDTO) -> TextToSpeechResultDTO:
        started = time.perf_counter()
        first_audio_ms = None
        chunks = []
        format_param = request.outputFormat or "mp3_22050_32"
        for chunk in self.stream(request):
            if first_audio_ms is None:
                first_audio_ms = int((time.perf_counter() - started) * 1000)
            chunks.append(chunk)
        total_ms = int((time.perf_counter() - started) * 1000)
        if not chunks:
            raise TextToSpeechError("ElevenLabs TTS returned no audio.")

        full_audio = b"".join(chunks)
        is_pcm = format_param.startswith("pcm_")

        return TextToSpeechResultDTO(
            audioPayloadBase64=None if is_pcm else base64.b64encode(full_audio).decode("ascii"),
            contentType=None if is_pcm else "audio/mpeg",
            pcmAudioBytes=full_audio if is_pcm else None,
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

    def stream(self, request: TextToSpeechRequestDTO, cancel_event: threading.Event | None = None):
        """Bounded pull stream: at most one 4800-byte PCM frame is read ahead."""
        query = urllib.parse.urlencode({"output_format": request.outputFormat or "mp3_22050_32", "language_code": self.language})
        http_request = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{urllib.parse.quote(self.voice_id)}/stream?{query}",
            data=json.dumps({"text": request.text, "model_id": self.model}).encode("utf-8"),
            headers={"Content-Type": "application/json", "xi-api-key": self._api_key}, method="POST")
        received = False
        try:
            if cancel_event and cancel_event.is_set():
                return
            with urllib.request.urlopen(http_request, timeout=30) as response:
                while not (cancel_event and cancel_event.is_set()):
                    chunk = response.read(4800)
                    if not chunk:
                        break
                    received = True
                    yield chunk
        except urllib.error.HTTPError as error:
            status = ""
            try:
                detail = json.loads(error.read(4096)).get("detail", {})
                status = detail.get("status", "") if isinstance(detail, dict) else ""
            except (ValueError, TypeError, AttributeError):
                pass
            code = "tts_quota_exceeded" if status in {"quota_exceeded", "insufficient_credits", "credit_balance_too_low"} or error.code == 402 else "tts_rate_limited" if error.code == 429 else "tts_synthesis_failed"
            raise TextToSpeechError("Speech synthesis unavailable.", code=code) from None
        except TimeoutError:
            raise TextToSpeechError("Speech synthesis timed out.", code="tts_timeout") from None
        except urllib.error.URLError as error:
            code = "tts_timeout" if isinstance(error.reason, TimeoutError) else "tts_connection_failed"
            raise TextToSpeechError("Speech synthesis connection failed.", code=code) from None
        except (OSError, http.client.HTTPException):
            raise TextToSpeechError("Speech synthesis connection failed.", code="tts_connection_failed") from None
        if not received and not (cancel_event and cancel_event.is_set()):
            raise TextToSpeechError("Speech synthesis returned no audio.", code="tts_empty_audio")
