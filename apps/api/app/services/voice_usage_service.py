"""Persist content-free, observational usage through the current user's JWT.

Requires migration 0010. Missing migration/network errors never break learning.
These measurements are estimates, never authoritative provider billing.
"""
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.services.voice_poc_metrics import EVENT_FIELDS, RATE_ENV, voice_poc_metrics

LATENCIES = ("stt_partial", "stt_final", "conversation_response", "tts_first_audio", "avatar_delivery", "conversation_first_token", "browser_first_frame", "browser_playback", "browser_end_to_end")
SUMMARY_FIELDS = frozenset(
    ["schema_version", "observation_count", "dropped_observations", "estimated_total_cost_usd"]
    + [f"count_{key}" for key in EVENT_FIELDS]
    + [f"usage_{key}" for key in RATE_ENV]
    + [f"estimated_{key}_cost_usd" for key in RATE_ENV]
    + [f"{name}_{key}" for name in LATENCIES for key in ("samples", "p50_ms", "p95_ms")]
    + ["actual_avatar_billable_seconds", "actual_stt_billable_seconds", "actual_tts_credits", "actual_cost_usd"]
)


def numeric_usage_summary(snapshot: dict[str, Any]) -> dict[str, float | int | None]:
    result = {"schema_version": 1, "observation_count": sum(snapshot["counts"].values()), "dropped_observations": snapshot["dropped_observations"], "estimated_total_cost_usd": snapshot["cost_usd"]["total"]}
    result.update({f"count_{key}": snapshot["counts"].get(key, 0) for key in EVENT_FIELDS})
    for key in RATE_ENV:
        result[f"usage_{key}"] = snapshot["usage"].get(key, 0)
        result[f"estimated_{key}_cost_usd"] = snapshot["cost_usd"]["components"].get(key)
    for name in LATENCIES:
        for key in ("samples", "p50_ms", "p95_ms"):
            result[f"{name}_{key}"] = snapshot["latency"].get(name, {}).get(key)
    # Provider reconciliation is deliberately unavailable until verified externally.
    for key in ("actual_avatar_billable_seconds", "actual_stt_billable_seconds", "actual_tts_credits", "actual_cost_usd"):
        result[key] = None
    for key, value in result.items():
        if key not in SUMMARY_FIELDS or (value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1e15)):
            raise ValueError("Invalid numeric usage summary")
    return result


def persist_voice_usage(client: Any, session_id: str) -> bool:
    """Best effort; caller must use a SupabaseUserClient, never service-role credentials."""
    try:
        summary = numeric_usage_summary(voice_poc_metrics.snapshot(session_id))
        if not summary["observation_count"]:
            return False  # Never replace saved observations with an empty post-restart cache.
        result = client.rpc("persist_voice_usage_summary", {"p_session_id": session_id, "p_summary": summary})
        return result is True
    except Exception:
        # No exception/provider payload logging. This optional telemetry cannot fail a turn.
        return False


# At most two network calls plus six queued tasks; completed tasks release tokens.
_usage_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="voice-usage")
_usage_slots = threading.BoundedSemaphore(8)


def schedule_voice_usage(client: Any, session_id: str) -> bool:
    """Schedule optional persistence without blocking a response or retaining unbounded JWTs."""
    if not _usage_slots.acquire(blocking=False):
        return False
    def persist_and_release() -> None:
        try:
            persist_voice_usage(client, session_id)
        finally:
            _usage_slots.release()
    try:
        _usage_executor.submit(persist_and_release)
        return True
    except RuntimeError:
        _usage_slots.release()
        return False
