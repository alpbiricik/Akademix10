"""Opt-in acceptance against a dedicated ALREADY COMPLETED learner test session.

Environment (never echoed): AKADEMX10_TEST_ACCESS_TOKEN,
AKADEMX10_TEST_OTHER_ACCESS_TOKEN, AKADEMX10_TEST_SESSION_ID;
optional AKADEMX10_TEST_API (defaults to loopback),
AKADEMX10_TEST_FINALIZE_BODY_JSON (exact original request, for same-key replay).
This does not create users, change training, generate answers or start audio.
Complete the full text-only training manually first. Never use production learners.
"""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid


class AcceptanceFailure(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward bearer credentials to another origin.


def request(api, path, token, body=None):
    encoded = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api + path, data=encoded, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return response.status, json.loads(response.read(2_000_000))
    except urllib.error.HTTPError as error:
        return error.code, None  # No error response, token or learner content output.
    except (OSError, ValueError):
        raise AcceptanceFailure("API unavailable or invalid response") from None


def check(condition, label):
    if not condition:
        raise AcceptanceFailure(label)


def run(api, token, other_token, session_id, finalize_body=None):
    results = []
    status, me = request(api, "/api/auth/me", token)
    check(status == 200 and isinstance(me, dict) and me.get("role") == "learner", "Primary learner authentication")
    status, other = request(api, "/api/auth/me", other_token)
    check(status == 200 and isinstance(other, dict) and other.get("role") == "learner", "Other learner authentication")
    check(me.get("id") != other.get("id") and me.get("companyId") and other.get("companyId") and me["companyId"] != other["companyId"], "Two distinct tenant test learners required")
    results.append("two_tenant_authentication")
    base = "/api/learner/sessions/" + session_id
    status, data = request(api, base, token)
    check(status == 200 and isinstance(data, dict), "Owner session read")
    session = data.get("session", {})
    check(session.get("userId") == me["id"] and session.get("companyId") == me["companyId"], "Session ownership")
    check(session.get("status") == "completed" and session.get("completedAt"), "Complete a dedicated text-only training before acceptance")
    results.append("completed_owner_session")
    before = {}
    for suffix in ("/report", "/scoring-results"):
        status, value = request(api, base + suffix, token)
        check(status == 200 and value, "Completed report and scoring read")
        before[suffix] = value
    results.append("persisted_report_and_scores_read")
    for suffix in ("", "/report", "/scoring-results", "/voice/metrics"):
        status, _ = request(api, base + suffix, other_token)
        check(status in (403, 404), "Cross-tenant read denied")
    results.append("cross_tenant_read_denied")
    conflict_body = {"idempotencyKey": "acceptance-" + str(uuid.uuid4()), "contractVersion": "2.0", "answers": []}
    status, _ = request(api, base + "/finalize", other_token, conflict_body)
    check(status in (403, 404), "Cross-tenant finalize denied")
    results.append("cross_tenant_finalize_denied")
    if finalize_body is not None:
        responses = []
        for _ in range(2):
            status, response = request(api, base + "/finalize", token, finalize_body)
            check(status == 200 and isinstance(response, dict) and response.get("status") == "completed", "Original finalize replay")
            responses.append(response)
        check(responses[0].get("evaluationId") and responses[0]["evaluationId"] == responses[1].get("evaluationId"), "Stable evaluation identity")
        check(responses[0].get("report") == responses[1].get("report") and responses[0].get("scoringResults") == responses[1].get("scoringResults"), "Stable replay results")
        results.append("same_key_finalize_replay")
    else:
        for _ in range(2):
            status, _ = request(api, base + "/finalize", token, conflict_body)
            check(status == 409, "Completed session rejects new finalize key")
        results.append("completed_session_new_key_conflict")
    for suffix, value in before.items():
        status, after = request(api, base + suffix, token)
        check(status == 200 and value == after, "Report unchanged after finalize retry")
    results.append("report_unchanged_after_retry")
    return {"passed": results, "not_verified": (["same_key_finalize_replay_requires_original_request"] if finalize_body is None else []) + ["full_training_browser_flow", "direct_database_RLS", "provider_invocation_count", "live_audio_quality_and_billing"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="store_true", help="Explicitly run authenticated network checks against a completed dedicated test session")
    args = parser.parse_args()
    if not args.run:
        print("No requests made. Configure dedicated test environment and pass --run.")
        return 0
    try:
        token = os.environ["AKADEMX10_TEST_ACCESS_TOKEN"]
        other = os.environ["AKADEMX10_TEST_OTHER_ACCESS_TOKEN"]
        session_id = str(uuid.UUID(os.environ["AKADEMX10_TEST_SESSION_ID"]))
        api = os.getenv("AKADEMX10_TEST_API", "http://127.0.0.1:8000").rstrip("/")
        parsed = urllib.parse.urlparse(api)
        check(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and parsed.path in ("", "/"), "API must be an origin without credentials")
        check(parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}), "HTTPS or loopback API required")
        raw = os.getenv("AKADEMX10_TEST_FINALIZE_BODY_JSON")
        body = json.loads(raw) if raw else None
        check(body is None or (isinstance(body, dict) and isinstance(body.get("idempotencyKey"), str) and isinstance(body.get("answers"), list)), "Invalid original finalize request")
        result = run(api, token, other, session_id, body)
    except (KeyError, ValueError):
        print("Dedicated test environment is missing or invalid; values were not logged.")
        return 1
    except AcceptanceFailure as error:
        print("Acceptance failed: " + str(error))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
