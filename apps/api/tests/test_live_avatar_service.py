import json
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from app.schemas.dtos import (
    LiveAvatarSessionActionRequestDTO,
    LiveAvatarSessionTokenRequestDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
)
from app.services import live_avatar_service
from app.services.conversation_errors import ConversationStateError
from app.services.live_avatar_provider import (
    HeyGenLiveAvatarProvider,
    LiveAvatarConfigurationError,
    LiveAvatarProviderError,
    get_live_avatar_provider,
)
from app.services.live_avatar_service import (
    ActiveAvatarSessionStore,
    create_avatar_token,
    speak_avatar,
    start_avatar_session,
    stop_avatar_session,
)
from tests.fakes import mock_store
from tests.fakes.providers import DeterministicLiveAvatarProvider as MockLiveAvatarProvider


class LiveAvatarServiceTests(unittest.TestCase):
    def setUp(self):
        self.session = deepcopy(mock_store.demo_session)
        self.avatar_state = deepcopy(next(s for s in mock_store.training_states if s.type == "avatar" or s.avatarEnabled))
        self.session.currentStateId = self.avatar_state.id
        self.store = ActiveAvatarSessionStore()

    def test_fake_provider_creates_token_with_livekit_details(self):
        provider = MockLiveAvatarProvider(avatar_id="avatar-tr-1", voice_id="voice-tr-1")
        token_response = provider.create_session_token(self.avatar_state.id)
        self.assertEqual(token_response.provider, "mock")
        self.assertTrue(token_response.sessionToken.startswith(f"test-avatar-token-{self.avatar_state.id}"))
        self.assertEqual(token_response.avatarId, "avatar-tr-1")
        self.assertEqual(token_response.voiceId, "voice-tr-1")
        self.assertEqual(token_response.metadata["livekitUrl"], "wss://test.livekit.local")

    def test_create_token_validates_avatar_state(self):
        # State not configured for avatar
        text_state = deepcopy(next(s for s in mock_store.training_states if s.type == "intro"))
        self.session.currentStateId = text_state.id
        with self.assertRaises(ConversationStateError):
            create_avatar_token(self.session, text_state)

    def test_create_token_allows_avatar_state(self):
        token_res = create_avatar_token(self.session, self.avatar_state, provider=MockLiveAvatarProvider(), store=self.store)
        self.assertIsNotNone(token_res.sessionToken)


    def test_avatar_session_start_and_stop_lifecycle(self):
        provider = MockLiveAvatarProvider()
        token = create_avatar_token(self.session, self.avatar_state, provider=provider, store=self.store)
        avatar_id = token.metadata["avatarSessionId"]
        # Start session
        start_res = start_avatar_session(self.session, self.avatar_state, avatar_id, provider=provider, store=self.store)
        self.assertEqual(start_res.status, "started")
        self.assertEqual(start_res.avatarSessionId, avatar_id)
        self.assertEqual(start_res.stateId, self.avatar_state.id)

        # Retrieve from store
        active = self.store.get(self.session.id, self.avatar_state.id)
        self.assertIsNotNone(active)
        self.assertEqual(active["avatarSessionId"], avatar_id)
        self.assertEqual(active["openCount"], 1)

        # Stop session
        stop_res = stop_avatar_session(self.session, self.avatar_state, avatar_id, provider=provider, store=self.store)
        self.assertEqual(stop_res.status, "stopped")
        self.assertEqual(stop_res.avatarSessionId, avatar_id)
        self.assertGreaterEqual(stop_res.activeSeconds, 0.0)

        # Store should now be empty for this session/state
        self.assertIsNone(self.store.get(self.session.id, self.avatar_state.id))

    def test_avatar_speak_action(self):
        provider = MockLiveAvatarProvider()
        self.store.register_start(self.session.id, self.avatar_state.id, "sess-123")
        speak_res = speak_avatar(self.session, self.avatar_state, "Merhaba, nasılsınız?", "sess-123", provider=provider, store=self.store)
        self.assertEqual(speak_res.status, "speaking")
        self.assertIsNone(speak_res.errorMessage)

    def test_avatar_speak_fallback_on_empty_session(self):
        provider = MockLiveAvatarProvider()
        speak_res = speak_avatar(self.session, self.avatar_state, "Merhaba", "", provider=provider, store=self.store)
        self.assertEqual(speak_res.status, "fallback")
        self.assertIsNotNone(speak_res.errorMessage)

    def test_heygen_provider_requires_api_key(self):
        with self.assertRaises(LiveAvatarConfigurationError):
            HeyGenLiveAvatarProvider(api_key="")

    @patch("urllib.request.urlopen")
    def test_heygen_provider_token_creation_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": {
                "token": "heygen-token-xyz",
                "livekit_url": "wss://test.livekit.cloud",
                "livekit_client_token": "lk-token",
            }
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response


        provider = HeyGenLiveAvatarProvider(api_key="test-heygen-key", avatar_id="avatar-1", voice_id="voice-1")
        res = provider.create_session_token("state-1")
        self.assertEqual(res.provider, "heygen")
        self.assertEqual(res.sessionToken, "heygen-token-xyz")
        self.assertEqual(res.avatarId, "avatar-1")

    @patch("urllib.request.urlopen")
    def test_heygen_provider_error_handling(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Connection timed out")
        provider = HeyGenLiveAvatarProvider(api_key="test-heygen-key")
        with self.assertRaises(LiveAvatarProviderError):
            provider.create_session_token("state-1")
