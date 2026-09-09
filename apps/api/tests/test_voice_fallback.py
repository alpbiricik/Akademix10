import base64
import io
import threading
import unittest
import wave
from copy import deepcopy
from unittest.mock import MagicMock, patch

from app.routers import learner
from app.schemas.dtos import ConversationTurnRequestDTO
from app.services import avatar_delivery
from app.services.conversation_cache import InMemoryConversationCache
from app.services.voice_turn_service import VoiceTurnOrchestrator
from tests.fakes import mock_store
from tests.fakes.providers import DeterministicConversationProvider
from tests.test_voice_services import FailingTTSProvider


class VoiceFallbackTests(unittest.TestCase):
    def test_legacy_answer_route_cannot_trigger_per_state_scoring(self):
        from fastapi import HTTPException
        with patch.object(learner, "_client"), patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner.scoring_service, "score_answer") as score:
            with self.assertRaises(HTTPException) as error:
                learner.post_answer(self.session.id, learner.AnswerRequest(stateId=self.state.id, answerText="An answer"), MagicMock())
            self.assertEqual(error.exception.detail["code"], "final_evaluation_required")
            score.assert_not_called()

    def setUp(self):
        self.session = deepcopy(mock_store.demo_session)
        self.state = deepcopy(next(s for s in mock_store.training_states if s.type == "roleplay"))
        self.session.currentStateId = self.state.id
        self.cache = InMemoryConversationCache()
        self.addCleanup(self.cache.close)
        self.addCleanup(avatar_delivery.deliveries.clear)

    def test_tts_failure_keeps_opening_text(self):
        result = VoiceTurnOrchestrator(self.session, self.state,
            conversation_provider=DeterministicConversationProvider(), tts_provider=FailingTTSProvider(), cache=self.cache).start_opening()
        self.assertTrue(result.assistantText)
        self.assertFalse(result.avatarSessionActive)
        self.assertEqual(result.tts.metadata.errorCode, "tts_synthesis_failed")

    def test_avatar_failure_returns_same_pcm_as_ephemeral_wav(self):
        threads = []
        real_thread = threading.Thread
        def thread(*args, **kwargs):
            created = real_thread(*args, **kwargs)
            threads.append(created)
            return created
        pcm = b"\x01\x00" * 48
        with patch("app.services.live_avatar_service.send_avatar_audio", return_value=False), patch.object(avatar_delivery.threading, "Thread", side_effect=thread):
            delivery_id = avatar_delivery.start_delivery(self.session, self.state, pcm)
            threads[0].join(2)
        result = avatar_delivery.delivery_status(self.session.id, delivery_id)
        self.assertEqual(result["status"], "fallback")
        with wave.open(io.BytesIO(base64.b64decode(result["audioPayloadBase64"]))) as audio:
            self.assertEqual(audio.getframerate(), 24000)
            self.assertEqual(audio.readframes(48), pcm)
        self.assertEqual(avatar_delivery.delivery_status("other-session", delivery_id), {"status": "expired"})
        avatar_delivery.deliveries._entries[avatar_delivery._key(self.session.id, delivery_id)].expires_at = 0
        self.assertEqual(avatar_delivery.delivery_status(self.session.id, delivery_id), {"status": "expired"})

    def test_text_only_conversation_never_calls_tts(self):
        client = MagicMock()
        with patch.object(learner, "_client", return_value=client), patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "state_from_row", return_value=self.state), patch.object(learner, "_synthesize_turn_tts") as tts:
            client.select.return_value = [{}]
            with patch.object(learner.conversation_service, "get_conversation_provider", return_value=DeterministicConversationProvider()):
                response = learner.post_conversation_turn(self.session.id,
                    ConversationTurnRequestDTO(stateId=self.state.id, learnerText="I would ask about renewal value and agree next steps.", textOnly=True), MagicMock())
            self.assertTrue(response.assistantText)
            self.assertIsNone(response.tts)
            tts.assert_not_called()

    def test_completing_last_state_does_not_mark_evaluation_completed(self):
        client = MagicMock()
        self.session.completedStateIds = []
        with patch.object(learner, "_client", return_value=client), patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "state_from_row", return_value=self.state):
            client.select.return_value = [{}]
            learner.patch_session_state(self.session.id, learner.StatePatchRequest(action="complete"), MagicMock())
        self.assertNotIn("status", client.patch.call_args.args[2])
