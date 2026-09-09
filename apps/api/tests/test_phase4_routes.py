"""Exercise real Bearer/profile/role dependencies; only external transport is fake."""
import asyncio
import json
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from app.main import app
from app.core import auth
from app.routers import learner
from app.services.conversation_cache import conversation_cache
from app.services.finalization_cache import finalization_cache
from app.services.finalization_service import MissingSessionAnswersError, FinalizeRequestDTO, _validate_answers
from tests.fakes import mock_store


def request(method, path, body=None, token="test-jwt"):
    messages = []
    async def run():
        async def receive():
            return {"type": "http.request", "body": json.dumps(body or {}).encode(), "more_body": False}
        async def send(message):
            messages.append(message)
        headers = [(b"content-type", b"application/json")]
        if token:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                   "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                   "query_string": b"", "root_path": "", "headers": headers,
                   "client": ("127.0.0.1", 123), "server": ("test", 80)}, receive, send)
    asyncio.run(run())
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, json.loads(payload) if payload else None


class Phase4RouteTests(unittest.TestCase):
    def setUp(self):
        self.session = deepcopy(mock_store.demo_session)
        self.state = deepcopy(next(s for s in mock_store.training_states if s.type == "roleplay"))
        self.state.completionRule = "answered"
        self.base = f"/api/learner/sessions/{self.session.id}"
        self.auth_client = MagicMock()
        self.role = "learner"
        def select(table, query):
            if table == "users":
                return [{"id": self.session.userId, "role": self.role, "status": "active"}]
            return [{"company_id": self.session.companyId}]
        self.auth_client.select.side_effect = select
        for p in [patch.object(auth, "verify_access_token", return_value={"id": self.session.userId}),
                  patch.object(auth, "SupabaseUserClient", return_value=self.auth_client)]:
            p.start()
            self.addCleanup(p.stop)
        self.client = MagicMock()
        self.addCleanup(conversation_cache.clear)
        self.addCleanup(finalization_cache.clear)
        conversation_cache.clear()
        finalization_cache.clear()

    def test_missing_bearer_and_wrong_role_rejected(self):
        self.assertEqual(request("GET", self.base + "/voice/metrics", token=None)[0], 401)
        self.role = "company"
        self.assertEqual(request("GET", self.base + "/voice/metrics")[0], 403)

    def test_cross_tenant_session_rejected_even_if_database_returns_row(self):
        with patch.object(learner, "_client", return_value=self.client), \
             patch.object(learner, "session_from_row", return_value=self.session):
            self.client.select.return_value = [{"id": self.session.id}]
            # Trusted membership is another company while session is unchanged.
            self.auth_client.select.side_effect = lambda table, query: (
                [{"id": self.session.userId, "role": "learner", "status": "active"}]
                if table == "users" else [{"company_id": "other-company"}])
            for suffix in ["/voice/metrics", "/report", "/scoring-results"]:
                self.assertIn(request("GET", self.base + suffix)[0], [403, 404])

    def test_numeric_metrics_reject_content_and_unknown_fields(self):
        with patch.object(learner, "_client", return_value=self.client), \
             patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "_session_state", return_value=self.state):
            good = {"stateId": self.state.id, "event": "browser_playback", "metrics": {"latency_ms": 25}}
            self.assertEqual(request("POST", self.base + "/voice/metrics", good)[0], 200)
            for metrics in [{"transcript": "private"}, {"latency_ms": -1}, {"latency_ms": True}]:
                self.assertEqual(request("POST", self.base + "/voice/metrics", {**good, "metrics": metrics})[0], 422)

    def test_recovery_preserves_available_answers(self):
        key = f"conversation:{self.session.id}:{self.state.id}"
        conversation_cache.put(key, {"turns": [{"learnerText": "Existing evidence"}]}, 300)
        with patch.object(learner, "_client", return_value=self.client), \
             patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "_session_state", return_value=self.state):
            self.assertEqual(request("POST", self.base + "/conversation/recover", {"stateId": self.state.id})[0], 409)
            self.client.patch.assert_not_called()
            conversation_cache.delete(key)
            self.assertEqual(request("POST", self.base + "/conversation/recover", {"stateId": self.state.id})[0], 200)
            self.assertEqual(self.client.patch.call_args.args[2]["current_state_id"], self.state.id)

    def test_missing_answers_identify_required_states(self):
        with self.assertRaises(MissingSessionAnswersError) as error:
            _validate_answers(FinalizeRequestDTO(idempotencyKey="test-missing", answers=[]), [self.state])
        self.assertEqual(error.exception.missing_state_ids, [self.state.id])

    def test_text_opening_generates_question_with_voice_disabled_without_tts(self):
        from app.schemas.dtos import ConversationResultDTO, ProviderMetadataDTO
        result = ConversationResultDTO(assistantText="What would you like to practice?", action="continue",
            providerMetadata=ProviderMetadataDTO(provider="test", model="test"))
        with patch.object(learner, "VOICE_ENABLED", False), \
             patch.object(learner, "_client", return_value=self.client), \
             patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "state_from_row", return_value=self.state), \
             patch.object(learner.conversation_service, "start_training_conversation", return_value=result) as opening, \
             patch.object(learner, "VoiceTurnOrchestrator") as voice:
            self.client.select.return_value = [{"id": self.state.id}]
            status, body = request("POST", self.base + "/voice/opening", {"stateId": self.state.id, "learnerText": "", "textOnly": True})
            self.assertEqual(status, 200)
            self.assertEqual(body["assistantText"], result.assistantText)
            self.assertFalse(body["avatarSessionActive"])
            self.assertIsNone(body["tts"]["audioPayloadBase64"])
            opening.assert_called_once()
            voice.assert_not_called()
            self.assertEqual(request("POST", self.base + "/voice/opening", {"stateId": self.state.id, "learnerText": ""})[0], 503)

    def test_preparation_uses_authorized_state_without_starting_avatar(self):
        with patch.object(learner, "VOICE_ENABLED", True), patch.object(learner, "LIVE_AVATAR_ENABLED", True), \
             patch.object(learner, "_client", return_value=self.client), \
             patch.object(learner, "_load_session", return_value=self.session), \
             patch.object(learner, "_session_state", return_value=self.state), \
             patch("app.services.prepared_opening.prepare_opening", return_value={"preparedOpeningId": "prepared", "assistantText": "Question?"}) as prepare, \
             patch.object(learner.live_avatar_service, "start_avatar_session") as avatar:
            status, body = request("POST", self.base + "/voice/opening/prepare", {"stateId": self.state.id})
            self.assertEqual(status, 200)
            self.assertEqual(body["preparedOpeningId"], "prepared")
            prepare.assert_called_once_with(self.session, self.state)
            avatar.assert_not_called()

    def test_nonretryable_conversation_quota_preserves_answer_without_retry(self):
        from app.services import conversation_service
        from app.services.conversation_errors import ConversationProviderError
        provider = MagicMock()
        failure = ConversationProviderError("Unavailable")
        failure.retryable = False
        provider.continue_conversation.side_effect = failure
        self.session.completedStateIds = []
        self.session.currentStateId = self.state.id
        result, _, complete, _ = conversation_service.continue_training_conversation(
            self.session, self.state, "I would listen and agree on a clear follow-up date.", provider=provider)
        self.assertTrue(complete)
        self.assertTrue(result.providerMetadata.fallbackUsed)
        provider.continue_conversation.assert_called_once()
        saved = conversation_cache.get(f"conversation:{self.session.id}:{self.state.id}")
        self.assertTrue(saved["turns"])
