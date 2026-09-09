import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.dtos import LiveAvatarSessionTokenResponseDTO
from app.services.live_avatar_service import (
    ActiveAvatarSessionStore, create_avatar_token, start_avatar_session, stop_avatar_session,
)


class AvatarLifecycleTests(unittest.TestCase):
    def test_start_cannot_bind_an_unissued_provider_session(self):
        from app.services.conversation_errors import ConversationStateError
        with self.assertRaises(ConversationStateError):
            start_avatar_session(self.session, self.state, "another-users-provider-session", self.provider, self.store)
        self.assertIsNone(self.store.get(self.session.id, self.state.id))

    def setUp(self):
        self.store = ActiveAvatarSessionStore()
        self.session = SimpleNamespace(id="learner-session")
        self.state = SimpleNamespace(id="state", avatarEnabled=True)
        self.provider = MagicMock(provider_name="mock", avatar_id="mock")

    def tearDown(self):
        self.store.clear()

    def token(self, avatar_id):
        return LiveAvatarSessionTokenResponseDTO(
            provider="mock", sessionToken="ephemeral", avatarId="avatar", voiceId="voice",
            quality="medium", sessionTimeoutSec=600,
            metadata={"avatarSessionId": avatar_id, "wsUrl": "ws://local"},
        )

    def test_ten_create_start_stop_cycles_and_repeated_stop(self):
        for cycle in range(10):
            avatar_id = f"avatar-{cycle}"
            self.provider.create_session_token.return_value = self.token(avatar_id)
            token = create_avatar_token(self.session, self.state, self.provider, self.store)
            self.assertIs(create_avatar_token(self.session, self.state, self.provider, self.store), token)
            for _ in range(2):
                start_avatar_session(self.session, self.state, avatar_id, self.provider, self.store)
            self.assertEqual(self.store.get(self.session.id, self.state.id)["openCount"], 1)
            for _ in range(2):
                stop_avatar_session(self.session, self.state, avatar_id, self.provider, self.store)
            self.assertIsNone(self.store.get(self.session.id, self.state.id))
        self.assertEqual(self.provider.create_session_token.call_count, 10)
        self.assertEqual(self.provider.stop_session.call_count, 10)

    def test_late_stop_cannot_remove_replacement_session(self):
        self.store.register_start(self.session.id, self.state.id, "new")
        stop_avatar_session(self.session, self.state, "old", self.provider, self.store)
        self.assertEqual(self.store.get(self.session.id, self.state.id)["avatarSessionId"], "new")
        self.provider.stop_session.assert_not_called()

    def test_stopping_one_learner_leaves_other_active(self):
        self.store.register_start(self.session.id, self.state.id, "first")
        self.store.register_start("another-learner", self.state.id, "second")
        stop_avatar_session(self.session, self.state, "first", self.provider, self.store)
        self.assertEqual(self.store.get("another-learner", self.state.id)["avatarSessionId"], "second")
        self.provider.stop_session.assert_called_once_with("first")

    def test_expired_token_is_not_reused(self):
        self.provider.create_session_token.side_effect = [self.token("old"), self.token("new")]
        with patch("app.services.live_avatar_service.time.time", return_value=100):
            create_avatar_token(self.session, self.state, self.provider, self.store)
        with patch("app.services.live_avatar_service.time.time", return_value=701):
            token = create_avatar_token(self.session, self.state, self.provider, self.store)
        self.assertEqual(token.metadata["avatarSessionId"], "new")

    def test_expiry_removes_token_and_stale_timer_does_not_remove_replacement(self):
        with patch("app.services.live_avatar_service.threading.Timer") as timer:
            self.provider.create_session_token.return_value = self.token("old")
            create_avatar_token(self.session, self.state, self.provider, self.store)
            old_expire = timer.call_args.args[1]
            old_expire()
            self.assertIsNone(self.store.get(self.session.id, self.state.id))
            self.provider.create_session_token.return_value = self.token("new")
            create_avatar_token(self.session, self.state, self.provider, self.store)
            old_expire()
            self.assertEqual(self.store.get(self.session.id, self.state.id)["avatarSessionId"], "new")
