import threading
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from app.schemas.dtos import TextToSpeechMetadataDTO, TextToSpeechResultDTO
from app.services import prepared_opening as service
from app.services.avatar_delivery import cancel_deliveries
from app.services.conversation_cache import InMemoryConversationCache
from app.services.conversation_errors import ConversationStateError
from app.services.text_to_speech_provider import TextToSpeechError
from tests.fakes import mock_store
from tests.test_voice_services import CountingConversationProvider


class PCMProvider:
    provider_name = "test"
    def __init__(self):
        self.calls = 0
    def synthesize(self, request):
        self.calls += 1
        return TextToSpeechResultDTO(pcmAudioBytes=b"00" * 240, textFallback=request.text,
            metadata=TextToSpeechMetadataDTO(provider="test", model="test", voice="test", language="tr", characterCount=len(request.text)))


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.session = deepcopy(mock_store.demo_session)
        self.state = deepcopy(next(s for s in mock_store.training_states if s.type == "roleplay"))
        self.session.currentStateId = self.state.id
        self.cache = InMemoryConversationCache()
        self.addCleanup(self.cache.close)
        self.addCleanup(service.cancel_prepared_openings, self.session.id)
        self.conversation = CountingConversationProvider()
        self.tts = PCMProvider()

    def prepare(self):
        return service.prepare_opening(self.session, self.state, self.conversation, self.tts, self.cache)

    def test_preparation_never_starts_avatar_and_duplicate_consumption_only_sends_once(self):
        with patch.object(service, "start_delivery", return_value="delivery") as send, patch.object(service.avatar_session_store, "get_token", return_value=object()):
            prepared = self.prepare()
            self.assertEqual(prepared, self.prepare())
            send.assert_not_called()
            first = service.consume_prepared_opening(self.session, self.state, prepared["preparedOpeningId"])
            second = service.consume_prepared_opening(self.session, self.state, prepared["preparedOpeningId"])
        self.assertEqual(first, second)
        self.assertEqual(self.conversation.calls, 1)
        self.assertEqual(self.tts.calls, 1)
        send.assert_called_once()
        self.assertIsNone(first.tts.pcmAudioBytes)

    def test_consume_requires_matching_id_and_active_avatar(self):
        prepared = self.prepare()
        with self.assertRaises(ConversationStateError):
            service.consume_prepared_opening(self.session, self.state, "wrong")
        with patch.object(service.avatar_session_store, "get_token", return_value=None), self.assertRaises(ConversationStateError):
            service.consume_prepared_opening(self.session, self.state, prepared["preparedOpeningId"])

    def test_cancel_prevents_late_tts_and_delivery(self):
        original = self.conversation.continue_conversation
        def conversation(request):
            result = original(request)
            cancel_deliveries(self.session.id, self.state.id)
            return result
        self.conversation.continue_conversation = conversation
        with self.assertRaises(ConversationStateError):
            self.prepare()
        self.assertEqual(self.tts.calls, 0)

    def test_quota_failure_preserves_text_without_avatar_ready_id(self):
        def fail(request):
            raise TextToSpeechError("Unavailable", code="tts_quota_exceeded")
        self.tts.synthesize = fail
        result = self.prepare()
        self.assertIsNone(result["preparedOpeningId"])
        self.assertTrue(result["assistantText"])
        self.assertEqual(result["errorCode"], "tts_quota_exceeded")
        self.assertEqual(result, self.prepare())

    def test_expired_preparation_cannot_be_delivered(self):
        result = self.prepare()
        with service._lock:
            service._entries[(self.session.id, self.state.id)]["expires"] = 0
        with self.assertRaises(ConversationStateError):
            service.consume_prepared_opening(self.session, self.state, result["preparedOpeningId"])

    def test_oversized_stream_stops_without_persisting_audio(self):
        closed = threading.Event()
        def stream(request):
            try:
                yield b"00" * 6
                yield b"00" * 6
            finally:
                closed.set()
        self.tts.stream = stream
        with patch.object(service, "MAX_ENTRY_BYTES", 16):
            result = self.prepare()
        self.assertEqual(result["errorCode"], "tts_capacity")
        self.assertTrue(closed.is_set())
        self.assertEqual(service._entries[(self.session.id, self.state.id)]["pcm"], b"")

    def test_prepared_cache_cannot_bypass_completed_state(self):
        result = self.prepare()
        self.session.completedStateIds.append(self.state.id)
        with self.assertRaises(ConversationStateError):
            self.prepare()
        with self.assertRaises(ConversationStateError):
            service.consume_prepared_opening(self.session, self.state, result["preparedOpeningId"])

    def test_concurrent_prepare_is_singleflight(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.prepare())) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(2)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(self.tts.calls, 1)
        self.assertEqual(self.conversation.calls, 1)
