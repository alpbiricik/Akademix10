import asyncio
import json
import time
import urllib.parse
from typing import AsyncIterator

from app.schemas.dtos import SpeechToTextEventDTO
from app.services.speech_to_text_provider import stt_metadata


class DeepgramSTTConfigurationError(Exception):
    code = "deepgram_stt_not_configured"


class DeepgramStreamingSpeechToTextProvider:
    provider_name = "deepgram"

    def __init__(
        self,
        api_key: str,
        model: str = "nova-3",
        language: str = "tr",
        endpointing_ms: int = 500,
        utterance_end_ms: int = 1000,
    ) -> None:
        if not api_key:
            raise DeepgramSTTConfigurationError("Deepgram STT requires a server-side API key.")
        self._api_key = api_key
        self.model = model
        self.language = language
        self.endpointing_ms = endpointing_ms
        self.utterance_end_ms = utterance_end_ms

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[SpeechToTextEventDTO]:
        import websockets

        started = time.perf_counter()
        first_partial_ms: int | None = None
        final_transcript_ms: int | None = None
        url = self._url()
        metadata = stt_metadata(self.provider_name, self.model, self.language)
        yield SpeechToTextEventDTO(type="stream_started", metadata=metadata)
        try:
            async with websockets.connect(url, additional_headers={"Authorization": f"Token {self._api_key}"}, close_timeout=2) as websocket:
                sender = asyncio.create_task(self._send_audio(websocket, audio_chunks))
                try:
                    async for message in websocket:
                        event = json.loads(message)
                        event_type = event.get("type")
                        elapsed_ms = int((time.perf_counter() - started) * 1000)
                        if event_type == "SpeechStarted":
                            yield SpeechToTextEventDTO(type="speech_started", metadata=metadata)
                            continue
                        if event_type == "UtteranceEnd":
                            yield SpeechToTextEventDTO(
                                type="utterance_end",
                                metadata=stt_metadata(self.provider_name, self.model, self.language, utterance_end_ms=elapsed_ms),
                            )
                            continue
                        transcript, confidence = self._transcript(event)
                        if not transcript:
                            continue
                        is_final = bool(event.get("is_final"))
                        speech_final = bool(event.get("speech_final"))
                        if is_final or speech_final:
                            final_transcript_ms = final_transcript_ms or elapsed_ms
                            yield SpeechToTextEventDTO(
                                type="final_transcript",
                                transcript=transcript,
                                isFinal=True,
                                speechFinal=speech_final,
                                metadata=stt_metadata(self.provider_name, self.model, self.language, confidence, first_partial_ms, final_transcript_ms),
                            )
                            if speech_final:
                                break
                        else:
                            first_partial_ms = first_partial_ms or elapsed_ms
                            yield SpeechToTextEventDTO(
                                type="partial_transcript",
                                transcript=transcript,
                                metadata=stt_metadata(self.provider_name, self.model, self.language, confidence, first_partial_ms),
                            )
                finally:
                    sender.cancel()
                    await self._safe_close(websocket)
        except TimeoutError:
            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="timeout"))
        except Exception:
            yield SpeechToTextEventDTO(type="error", metadata=stt_metadata(self.provider_name, self.model, self.language, error_code="provider_error"))
        yield SpeechToTextEventDTO(type="stream_closed", metadata=metadata)

    def _url(self) -> str:
        query = urllib.parse.urlencode(
            {
                "model": self.model,
                "language": self.language,
                "interim_results": "true",
                "vad_events": "true",
                "endpointing": str(self.endpointing_ms),
                "utterance_end_ms": str(self.utterance_end_ms),
            }
        )
        return f"wss://api.deepgram.com/v1/listen?{query}"

    async def _send_audio(self, websocket, audio_chunks: AsyncIterator[bytes]) -> None:
        async for chunk in audio_chunks:
            if chunk:
                await websocket.send(chunk)
        await websocket.send(json.dumps({"type": "CloseStream"}))

    async def _safe_close(self, websocket) -> None:
        try:
            await websocket.close()
        except Exception:
            return

    def _transcript(self, event: dict) -> tuple[str, float | None]:
        alternatives = ((event.get("channel") or {}).get("alternatives") or [])
        if not alternatives:
            return "", None
        first = alternatives[0]
        return (first.get("transcript") or "").strip(), first.get("confidence")
