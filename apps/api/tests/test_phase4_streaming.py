import base64
import io
import http.client
import json
import threading
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.elevenlabs_tts_provider import ElevenLabsTextToSpeechProvider
from app.services.text_to_speech_provider import TextToSpeechError
from app.schemas.dtos import TextToSpeechRequestDTO
from app.services.gemini_conversation_provider import GeminiConversationProvider
from app.services.live_avatar_provider import HeyGenLiveAvatarProvider
from app.services import avatar_delivery
from app.services.live_avatar_provider import _pcm_frames, _wait_for_audio_deadline


class StreamingTests(unittest.TestCase):
    def test_pcm_stream_reframes_arbitrary_chunks_on_sample_boundaries(self):
        frames = list(_pcm_frames([b"a" * 1000, b"b" * 3800, b"c" * 2, b"d" * 4798, b"e" * 100]))
        self.assertEqual([len(frame) for frame in frames], [4800, 4800, 100])
        self.assertEqual(b"".join(frames), b"a" * 1000 + b"b" * 3800 + b"c" * 2 + b"d" * 4798 + b"e" * 100)

    def test_pcm_stream_rejects_partial_final_sample(self):
        with self.assertRaisesRegex(ValueError, "partial sample"):
            list(_pcm_frames([b"a" * 4801]))

    def test_deadline_pacing_subtracts_network_send_time(self):
        with patch("app.services.live_avatar_provider.time.monotonic", return_value=0.01), \
             patch("app.services.live_avatar_provider.time.sleep") as sleep:
            deadline = _wait_for_audio_deadline(0.0, 4800)
        self.assertAlmostEqual(deadline, 0.1)
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.09)

    def test_deadline_pacing_resets_after_long_stall_without_burst(self):
        with patch("app.services.live_avatar_provider.time.monotonic", side_effect=[0.35, 0.36]), \
             patch("app.services.live_avatar_provider.time.sleep") as sleep:
            deadline = _wait_for_audio_deadline(0.0, 4800)
            deadline = _wait_for_audio_deadline(deadline, 4800)
        self.assertAlmostEqual(deadline, 0.45)
        self.assertEqual(sleep.call_count, 1)
        self.assertAlmostEqual(sleep.call_args.args[0], 0.09)

    def test_ten_frames_follow_one_monotonic_timeline(self):
        clock = [0.0]
        ws = MagicMock()
        def send(_payload):
            clock[0] += 0.01
        def sleep(delay):
            clock[0] += delay
        ws.send.side_effect = send
        provider = HeyGenLiveAvatarProvider("test")
        with patch.object(provider, "_ws_pool", {"url": ws}), \
             patch("app.services.live_avatar_provider.time.monotonic", side_effect=lambda: clock[0]), \
             patch("app.services.live_avatar_provider.time.sleep", side_effect=sleep):
            self.assertTrue(provider.send_audio("url", b"00" * 24000))
        # Ten 100ms frames start over a 900ms window. Network overhead is
        # absorbed into the deadlines rather than added nine times.
        self.assertAlmostEqual(clock[0], 0.92, places=6)
        self.assertEqual(ws.send.call_count, 11)  # ten frames and speak_end

    def test_live_stream_reframes_chunks_and_preserves_end_order(self):
        ws = MagicMock()
        payloads = []
        ws.send.side_effect = lambda payload: payloads.append(json.loads(payload))
        provider = HeyGenLiveAvatarProvider("test")
        with patch.object(provider, "_ws_pool", {"url": ws}), \
             patch("app.services.live_avatar_provider._wait_for_audio_deadline", return_value=0.1):
            self.assertTrue(provider.send_audio_stream(
                "url", iter([b"a" * 6000, b"b" * 3700]), threading.Event()))
        audio = [base64.b64decode(item["audio"]) for item in payloads if item["type"] == "agent.speak"]
        self.assertEqual([len(frame) for frame in audio], [4800, 4800, 100])
        self.assertEqual(b"".join(audio), b"a" * 6000 + b"b" * 3700)
        self.assertEqual(payloads[-1]["type"], "agent.speak_end")

    def test_buffered_read_failures_preserve_typed_fallback(self):
        for failure in [ConnectionResetError("private"), BrokenPipeError("private"), http.client.IncompleteRead(b"private")]:
            with self.subTest(failure=type(failure).__name__), patch("urllib.request.urlopen") as open_url:
                open_url.return_value.__enter__.return_value.read.side_effect = failure
                with self.assertRaises(TextToSpeechError) as raised:
                    ElevenLabsTextToSpeechProvider("test").synthesize(TextToSpeechRequestDTO(text="test"))
                self.assertEqual(raised.exception.code, "tts_connection_failed")
                self.assertNotIn("private", str(raised.exception))

    def test_cancel_counts_active_jobs_once(self):
        event = threading.Event()
        with patch.dict(avatar_delivery._jobs, {"test-cancel": ("cancel-owner", "state", event)}, clear=True), \
             patch("app.services.voice_poc_metrics.voice_poc_metrics.record") as record:
            avatar_delivery.cancel_deliveries("cancel-owner", "state")
            avatar_delivery.cancel_deliveries("cancel-owner", "state")
        record.assert_called_once_with("cancel-owner", "state", "cancel")

    def test_tts_is_pull_bounded_and_closes_on_cancel(self):
        response = MagicMock()
        response.read.side_effect = [b"a" * 4800, b"b" * 4800, b""]
        event = threading.Event()
        with patch("urllib.request.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = response
            stream = ElevenLabsTextToSpeechProvider("test").stream(TextToSpeechRequestDTO(text="test", outputFormat="pcm_24000"), event)
            self.assertEqual(len(next(stream)), 4800)
            response.read.assert_called_once_with(4800)
            event.set()
            self.assertEqual(list(stream), [])
            open_url.return_value.__exit__.assert_called_once()

    def test_safe_quota_and_rate_codes(self):
        for status, http, code in [("quota_exceeded", 401, "tts_quota_exceeded"), ("too_many_requests", 429, "tts_rate_limited")]:
            error = urllib.error.HTTPError("private", http, "secret", {}, io.BytesIO(json.dumps({"detail": {"status": status}}).encode()))
            with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(TextToSpeechError) as raised:
                list(ElevenLabsTextToSpeechProvider("test").stream(TextToSpeechRequestDTO(text="test")))
            self.assertEqual(raised.exception.code, code)
            self.assertNotIn("secret", str(raised.exception))

    def test_gemini_assembles_before_parsing(self):
        def frame(text):
            return b"data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode() + b"\n\n"
        response = io.BytesIO(frame('{"assistantText":') + frame('"Merhaba","action":"continue"}'))
        with patch("app.services.voice_poc_metrics.voice_poc_metrics.record") as metric:
            body = GeminiConversationProvider("test")._read_stream(response, SimpleNamespace(sessionId="s", stateId="t"), 0)
        self.assertEqual(json.loads(GeminiConversationProvider("test")._extract_text(body))["assistantText"], "Merhaba")
        metric.assert_called_once()

    def test_stream_cancel_stops_next_frame_and_closes_socket(self):
        event = threading.Event()
        ws = MagicMock()
        ws.send.side_effect = lambda message: event.set()
        provider = HeyGenLiveAvatarProvider("test")
        with patch.object(provider, "_ws_pool", {"url": ws}):
            with self.assertRaises(RuntimeError):
                provider.send_audio_stream("url", iter([b"00", b"11"]), event)
        ws.send.assert_called_once()
        ws.close.assert_called_once()

    def test_cancelled_generation_cannot_start_late_delivery(self):
        session, state = SimpleNamespace(id="late"), SimpleNamespace(id="state")
        generation = avatar_delivery.delivery_generation(session.id, state.id)
        avatar_delivery.cancel_deliveries(session.id, state.id)
        provider = MagicMock()
        self.assertIsNone(avatar_delivery.start_stream_delivery(session, state, provider, None, generation))
        self.assertIsNone(avatar_delivery.start_delivery(session, state, b"00", generation))
        provider.stream.assert_not_called()

    def test_partial_stream_failure_never_exposes_replay_audio(self):
        def send(session, state, chunks, cancel):
            next(chunks)
            raise TextToSpeechError("Unavailable", code="tts_quota_exceeded")
        provider = MagicMock()
        provider.stream.return_value = iter([b"00", b"11"])
        session, state = SimpleNamespace(id="partial"), SimpleNamespace(id="state")
        threads = []
        real_thread = threading.Thread
        def thread(*args, **kwargs):
            t = real_thread(*args, **kwargs)
            threads.append(t)
            return t
        with patch("app.services.live_avatar_service.send_avatar_audio_stream", side_effect=send), patch.object(avatar_delivery.threading, "Thread", side_effect=thread):
            delivery = avatar_delivery.start_stream_delivery(session, state, provider, SimpleNamespace(text="test"))
            threads[0].join(2)
        result = avatar_delivery.delivery_status(session.id, delivery)
        self.assertEqual(result, {"status": "text_only", "errorCode": "tts_quota_exceeded"})

    def test_buffered_partial_failure_does_not_return_replayable_audio(self):
        from app.services.live_avatar_provider import LiveAvatarPartialAudioError
        ws = MagicMock()
        ws.send.side_effect = [None, OSError("disconnected")]
        provider = HeyGenLiveAvatarProvider("test")
        with patch.object(provider, "_ws_pool", {"url": ws}), patch("app.services.live_avatar_provider.time.sleep"):
            with self.assertRaises(LiveAvatarPartialAudioError):
                provider.send_audio("url", b"00" * 4800)
        ws.close.assert_called_once()

    def test_empty_tts_audio_is_explicit(self):
        with patch("urllib.request.urlopen") as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b""
            with self.assertRaises(TextToSpeechError) as error:
                list(ElevenLabsTextToSpeechProvider("test").stream(TextToSpeechRequestDTO(text="test")))
        self.assertEqual(error.exception.code, "tts_empty_audio")

    def test_stream_frame_memory_bound(self):
        from app.services.conversation_errors import ConversationProviderError
        with self.assertRaises(ConversationProviderError):
            GeminiConversationProvider("test")._read_stream(io.BytesIO(b"data: " + b"x" * 65537), SimpleNamespace(sessionId="s", stateId="t"), 0)
