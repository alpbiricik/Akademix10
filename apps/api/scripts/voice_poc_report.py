"""Export content-free POC measurements using a learner's normal JWT.

Usage: set AKADEMX10_TEST_ACCESS_TOKEN outside shell history, then:
python apps/api/scripts/voice_poc_report.py --session-id UUID --output report.json
Never prints tokens, request headers, provider payloads or conversation content.
"""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the current session's numeric voice POC report.")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.getenv("AKADEMX10_TEST_ACCESS_TOKEN")
    if not token:
        parser.error("Set AKADEMX10_TEST_ACCESS_TOKEN to a dedicated learner test session JWT.")
    parsed = urllib.parse.urlparse(args.api)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        parser.error("Use HTTPS or a loopback development API.")
    url = args.api.rstrip("/") + "/api/learner/sessions/" + urllib.parse.quote(args.session_id, safe="") + "/voice/metrics"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            report = json.loads(response.read())
    except (OSError, urllib.error.URLError, ValueError):
        print("Metrics unavailable. Check the API and the dedicated learner login.")
        return 1
    fields = ("schema_version", "counts", "usage", "latency", "cost_usd", "provider_billing", "dropped_observations", "live_gate", "limitations")
    # Only the metrics contract is exported; never arbitrary response keys.
    safe_report = {field: report[field] for field in fields if field in report}
    args.output.write_text(json.dumps(safe_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Numeric POC report exported. Live quality and billing still require review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
