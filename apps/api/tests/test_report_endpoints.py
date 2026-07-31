import asyncio
import json
import unittest
from copy import deepcopy
from urllib.parse import urlencode

from app.main import app
from app.schemas.dtos import DimensionScoreDTO, ProviderMetadataDTO, SkillImpactDTO, StructuredScoringResultDTO
from app.services import mock_store, scoring_repository


def make_result(session_id: str, state_id: str, overall: int, generated_at: str, answer_ref: str | None = None) -> StructuredScoringResultDTO:
    return StructuredScoringResultDTO(
        sessionId=session_id,
        stateId=state_id,
        answerRef=answer_ref or f"{session_id}:{state_id}:{generated_at}",
        rubricId="rubric-template-sales-communication-v1",
        rubricVersion="1.0",
        overallScore=overall,
        dimensionScores=[
            DimensionScoreDTO(dimensionId="clarity", name="Clarity", score=overall, rationale=""),
            DimensionScoreDTO(dimensionId="empathy", name="Empathy", score=max(0, overall - 10), rationale=""),
        ],
        conciseLearnerFeedback="Endpoint safe feedback.",
        strengths=["Clear response"],
        improvementAreas=["Ask one more question"],
        recommendedNextAction="complete_state",
        skillImpacts=[
            SkillImpactDTO(skill="Communication", delta=2, score=overall, sourceDimensionIds=["clarity"]),
            SkillImpactDTO(skill="Empathy", delta=1, score=max(0, overall - 10), sourceDimensionIds=["empathy"]),
        ],
        providerMetadata=ProviderMetadataDTO(provider="mock", model="deterministic-mock-v1"),
        generatedAt=generated_at,
    )


def asgi_request(method: str, path: str, role: str | None = None, query: dict[str, str] | None = None, body: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    messages = []
    body_bytes = json.dumps(body or {}).encode("utf-8") if body is not None else b""
    headers = [(b"content-type", b"application/json")]
    if role:
        headers.append((b"x-mock-role", role.encode("utf-8")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": urlencode(query or {}).encode("utf-8"),
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    payload = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, json.loads(payload.decode("utf-8")) if payload else {}


class ReportEndpointTests(unittest.TestCase):
    def setUp(self):
        scoring_repository.reset_mock_scoring_store()
        mock_store.sessions.clear()
        self.session = deepcopy(mock_store.demo_session)
        self.session.status = "completed"
        self.session.completedStateIds = [state.id for state in mock_store.training_states]
        self.session.completedAt = "2026-07-29T10:00:00.000Z"
        self.secondary = self.session.model_copy(deep=True)
        self.secondary.id = "other-learner-session"
        self.secondary.userId = "user-learner-other"
        self.other_company = self.session.model_copy(deep=True)
        self.other_company.id = "other-company-session"
        self.other_company.companyId = "company-secondary"
        mock_store.sessions[self.session.id] = self.session
        mock_store.sessions[self.secondary.id] = self.secondary
        mock_store.sessions[self.other_company.id] = self.other_company
        state_1 = mock_store.training_states[3].id
        state_2 = mock_store.training_states[5].id
        scoring_repository.save_scoring_result(make_result(self.session.id, state_1, 80, "2026-07-29T10:00:00.000Z"))
        scoring_repository.save_scoring_result(make_result(self.session.id, state_2, 90, "2026-07-29T10:05:00.000Z"))
        scoring_repository.save_scoring_result(make_result(self.secondary.id, state_1, 70, "2026-07-29T10:06:00.000Z"))
        scoring_repository.save_scoring_result(make_result(self.other_company.id, state_1, 10, "2026-07-29T10:07:00.000Z", answer_ref="other-company-ref"))

    def test_learner_can_read_own_session_scoring_results(self):
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/scoring-results", "learner")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload), 2)
        self.assertEqual([item["stateId"] for item in payload], sorted(item["stateId"] for item in payload))

    def test_learner_can_read_own_session_report(self):
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/report", "learner")
        self.assertEqual(status, 200)
        self.assertEqual(payload["reportType"], "learner_session")
        self.assertEqual(payload["sessionId"], self.session.id)
        self.assertEqual(payload["overallScore"], 85)

    def test_learner_cannot_access_other_learner_session(self):
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.secondary.id}/report", "learner")
        self.assertEqual(status, 404)
        self.assertEqual(payload["detail"]["code"], "report_not_found")

    def test_company_can_read_own_aggregate_report(self):
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company")
        self.assertEqual(status, 200)
        self.assertEqual(payload["reportType"], "company_aggregate")
        self.assertEqual(payload["company"]["id"], "company-demo")

    def test_company_report_excludes_other_company_data(self):
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company")
        self.assertEqual(status, 200)
        self.assertNotIn("company-secondary", json.dumps(payload))
        self.assertNotIn("other-company-ref", json.dumps(payload))
        self.assertNotEqual(payload["averageOverallScore"], 10)

    def test_company_id_injection_does_not_expand_scope(self):
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company", query={"companyId": "company-secondary"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["company"]["id"], "company-demo")
        self.assertNotIn("company-secondary", json.dumps(payload))

    def test_platform_can_read_aggregate_report(self):
        status, payload = asgi_request("GET", "/api/platform/reports/aggregate", "platform")
        self.assertEqual(status, 200)
        self.assertEqual(payload["reportType"], "platform_aggregate")
        self.assertEqual(payload["companyCount"], len(mock_store.companies))

    def test_learner_cannot_access_company_or_platform_endpoints(self):
        company_status, _ = asgi_request("GET", "/api/company/reports/aggregate", "learner")
        platform_status, _ = asgi_request("GET", "/api/platform/reports/aggregate", "learner")
        self.assertEqual(company_status, 403)
        self.assertEqual(platform_status, 403)

    def test_company_cannot_access_learner_or_platform_endpoints(self):
        learner_status, _ = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/report", "company")
        platform_status, _ = asgi_request("GET", "/api/platform/reports/aggregate", "company")
        self.assertEqual(learner_status, 403)
        self.assertEqual(platform_status, 403)

    def test_platform_policy_is_platform_only_for_platform_endpoint(self):
        status, _ = asgi_request("GET", "/api/platform/reports/aggregate", "platform")
        self.assertEqual(status, 200)

    def test_invalid_role_is_rejected(self):
        status, payload = asgi_request("GET", "/api/platform/reports/aggregate", "admin")
        self.assertEqual(status, 403)
        self.assertEqual(payload["detail"], "Invalid mock role.")

    def test_missing_or_inaccessible_session_safe_error(self):
        status, payload = asgi_request("GET", "/api/learner/sessions/missing-session/report", "learner")
        self.assertEqual(status, 404)
        self.assertEqual(payload["detail"]["message"], "Session not found.")

    def test_empty_report_dataset_safe_response(self):
        scoring_repository.reset_mock_scoring_store()
        mock_store.sessions.clear()
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company")
        self.assertEqual(status, 200)
        self.assertEqual(payload["scoredSessionCount"], 0)
        self.assertTrue(payload["coverage"]["insufficientSample"])

    def test_partial_session_report_is_preserved(self):
        self.session.status = "in_progress"
        self.session.completedAt = None
        mock_store.sessions[self.session.id] = self.session
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/report", "learner")
        self.assertEqual(status, 200)
        self.assertTrue(payload["coverage"]["isPartial"])

    def test_duplicate_scoring_result_is_not_counted_twice(self):
        state_id = mock_store.training_states[3].id
        scoring_repository.save_scoring_result(make_result(self.session.id, state_id, 60, "2026-07-29T09:00:00.000Z", answer_ref="older"))
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/scoring-results", "learner")
        self.assertEqual(status, 200)
        self.assertEqual(len([item for item in payload if item["stateId"] == state_id]), 1)

    def test_deterministic_response_output(self):
        first = asgi_request("GET", "/api/company/reports/aggregate", "company")[1]
        second = asgi_request("GET", "/api/company/reports/aggregate", "company")[1]
        self.assertEqual(first, second)

    def test_invalid_date_format_is_rejected(self):
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company", query={"dateFrom": "not-a-date"})
        self.assertEqual(status, 422)
        self.assertEqual(payload["detail"]["code"], "invalid_report_filter")

    def test_invalid_date_range_is_rejected(self):
        status, payload = asgi_request("GET", "/api/company/reports/aggregate", "company", query={"dateFrom": "2026-08-01T00:00:00Z", "dateTo": "2026-07-01T00:00:00Z"})
        self.assertEqual(status, 422)
        self.assertEqual(payload["detail"]["code"], "invalid_report_filter")

    def test_aggregate_responses_do_not_leak_sensitive_fields(self):
        _, company_payload = asgi_request("GET", "/api/company/reports/aggregate", "company")
        _, platform_payload = asgi_request("GET", "/api/platform/reports/aggregate", "platform")
        combined = json.dumps({"company": company_payload, "platform": platform_payload}).lower()
        for forbidden in ["answertext", "stateprompt", "system instruction", "raw provider", "secret"]:
            self.assertNotIn(forbidden, combined)

    def test_schema_version_propagation(self):
        status, payload = asgi_request("GET", f"/api/learner/sessions/{self.session.id}/report", "learner")
        self.assertEqual(status, 200)
        self.assertEqual(payload["schemaVersion"], "1.0")
        self.assertEqual(payload["sourceScoringSchemaVersions"], ["1.0"])

    def test_existing_answer_submit_contract(self):
        scoring_repository.reset_mock_scoring_store()
        status, payload = asgi_request(
            "POST",
            f"/api/learner/sessions/{self.session.id}/answers",
            "learner",
            body={"stateId": mock_store.training_states[3].id, "answerText": "I understand the concern. What outcome matters most?"},
        )
        self.assertEqual(status, 200)
        self.assertIn("session", payload)
        self.assertIn("feedback", payload)
        self.assertIn("scoringResult", payload)

    def test_get_requests_do_not_create_provider_scoring(self):
        before = len(scoring_repository.list_scoring_results())
        asgi_request("GET", "/api/company/reports/aggregate", "company")
        asgi_request("GET", "/api/platform/reports/aggregate", "platform")
        after = len(scoring_repository.list_scoring_results())
        self.assertEqual(before, after)

    def test_openapi_contains_report_endpoints(self):
        status, payload = asgi_request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("/api/learner/sessions/{session_id}/scoring-results", payload["paths"])
        self.assertIn("/api/learner/sessions/{session_id}/report", payload["paths"])
        self.assertIn("/api/company/reports/aggregate", payload["paths"])
        self.assertIn("/api/platform/reports/aggregate", payload["paths"])


if __name__ == "__main__":
    unittest.main()
