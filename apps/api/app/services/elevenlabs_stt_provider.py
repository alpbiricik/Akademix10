import asyncio
import base64
import json
import time
import urllib.parse
from typing import AsyncIterator

from app.schemas.dtos import SpeechToTextEventDTO
from app.services.speech_to_text_provider import stt_metadata


class ElevenLabsSTTConfigurationError(Exception):
    code = "elevenlabs_stt_not_configured"


class ElevenLabsSpeechToTextProvider:
    provider_name = "elevenlabs"
    audio_format = "pcm_16000"
    sample_rate = 16000

    def __init__(
        self,
        api_key: str,
        model: str = "scribe_v2_realtime",
        language: str = "tr",
        commit_strategy: str = "vad",
        vad_silence_threshold_secs: float = 0.8,
    ) -> None:
        if not api_key:
            raise ElevenLabsSTTConfigurationError("ElevenLabs STT requires a server-side API key.")
        self._api_key = api_key
        self.model = model
        self.language = language
        self.commit_strategy = commit_strategy
        self.vad_silence_threshold_secs = vad_silence_threshold_secs

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[SpeechToTextEventDTO]:
        import websockets

        started = time.perf_counter()
        first_partial_ms: int | None = None
        final_ms: int | None = None
        metadata = stt_metadata(self.provider_name, self.model, self.language)
        try:
            async with websockets.connect(self._url(), additional_headers={"xi-api-key": self._api_key}, close_timeout=2) as websocket:
                sender = asyncio.create_task(self._send_audio(websocket, audio_chunks))
                try:
                    while True:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        try:
                            event = json.loads(message)
                        except json.JSONDecodeError:
                            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="invalid_provider_event"))
                            continue
                        event_type = event.get("message_type") or event.get("type")
                        elapsed_ms = int((time.perf_counter() - started) * 1000)
                        if event_type == "session_started":
                            yield SpeechToTextEventDTO(type="stream_started", metadata=metadata)
                            continue
                        mapped = self._map_transcript_event(event, elapsed_ms, first_partial_ms, final_ms)
                        if mapped:
                            if mapped.type == "partial_transcript":
                                first_partial_ms = first_partial_ms or elapsed_ms
                            if mapped.type in {"final_transcript", "committed_transcript"}:
                                final_ms = final_ms or elapsed_ms
                            yield mapped
                            if mapped.type in {"final_transcript", "committed_transcript"}:
                                break
                            continue
                        if event_type in {"auth_error", "quota_exceeded", "rate_limited", "resource_exhausted", "input_error", "transcriber_error", "error"}:
                            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code=str(event_type)))
                            break
                finally:
                    sender.cancel()
                    await self._safe_close(websocket)
        except TimeoutError:
            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="timeout"))
        except Exception:
            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="provider_error"))
        yield SpeechToTextEventDTO(type="stream_closed", metadata=metadata)

    def _url(self) -> str:
        query = {
            "model_id": self.model,
            "language_code": self.language,
            "audio_format": self.audio_format,
            "sample_rate": str(self.sample_rate),
            "commit_strategy": self.commit_strategy,
            "vad_silence_threshold_secs": str(self.vad_silence_threshold_secs),
        }
        return f"wss://api.elevenlabs.io/v1/speech-to-text/realtime?{urllib.parse.urlencode(query)}"

    async def _send_audio(self, websocket, audio_chunks: AsyncIterator[bytes]) -> None:
        async for chunk in audio_chunks:
            if not chunk:
                continue
            await websocket.send(
                json.dumps(
                    {
                        "message_type": "input_audio_chunk",
                        "audio_base_64": base64.b64encode(chunk).decode("ascii"),
                        "sample_rate": self.sample_rate,
                    }
                )
            )
        if self.commit_strategy != "vad":
            await websocket.send(json.dumps({"message_type": "input_audio_chunk", "audio_base_64": "", "commit": True, "sample_rate": self.sample_rate}))

    async def _safe_close(self, websocket) -> None:
        try:
            await websocket.close()
        except Exception:
            return

    def _map_transcript_event(
        self,
        event: dict,
        elapsed_ms: int,
        first_partial_ms: int | None = None,
        final_ms: int | None = None,
    ) -> SpeechToTextEventDTO | None:
        event_type = event.get("message_type") or event.get("type")
        text = (event.get("text") or "").strip()
        if not text:
            return None
        if event_type == "partial_transcript":
            return SpeechToTextEventDTO(
                type="partial_transcript",
                transcript=text,
                metadata=stt_metadata(self.provider_name, self.model, self.language, first_partial_ms=first_partial_ms or elapsed_ms),
            )
        if event_type in {"final_transcript", "committed_transcript", "committed_transcript_with_timestamps"}:
            return SpeechToTextEventDTO(
                type="committed_transcript" if str(event_type).startswith("committed") else "final_transcript",
                transcript=text,
                isFinal=True,
                speechFinal=True,
                metadata=stt_metadata(
                    self.provider_name,
                    self.model,
                    self.language,
                    first_partial_ms=first_partial_ms,
                    final_transcript_ms=final_ms or elapsed_ms,
                    utterance_end_ms=elapsed_ms,
                ),
            )
        return None
