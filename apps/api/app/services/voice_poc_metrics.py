"""Ephemeral, bounded numeric observations. Never accepts transcripts or provider payloads."""
import math
import os
import threading
from typing import Any

from app.core.config import CONVERSATION_CONTEXT_TTL_SECONDS
from app.services.conversation_cache import InMemoryConversationCache

EVENT_FIELDS = {
    "conversation_first_token": {"latency_ms"},
    "browser_first_frame": {"latency_ms"},
    "browser_playback": {"latency_ms"},
    "browser_end_to_end": {"latency_ms"},
    "retry": set(),
    "cancel": set(),
    "stt_partial": {"latency_ms"},
    "stt": {"latency_ms", "audio_seconds"},
    "conversation": {"latency_ms", "input_tokens", "output_tokens"},
    "tts": {"first_audio_ms", "characters"},
    "avatar_start": set(),
    "avatar_stop": {"duration_seconds"},
    "avatar_delivery": {"latency_ms"},
    "fallback": set(),
    "error": set(),
}
RATE_ENV = {
    "input_tokens": ("VOICE_POC_INPUT_USD_PER_MILLION_TOKENS", 1_000_000),
    "output_tokens": ("VOICE_POC_OUTPUT_USD_PER_MILLION_TOKENS", 1_000_000),
    "tts_characters": ("VOICE_POC_TTS_USD_PER_THOUSAND_CHARACTERS", 1000),
    "audio_seconds": ("VOICE_POC_STT_USD_PER_MINUTE", 60),
    "avatar_seconds": ("VOICE_POC_AVATAR_USD_PER_MINUTE", 60),
}


def _percentiles(values: list[float]) -> dict[str, float | int | None]:
    ordered = sorted(values)
    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = (len(ordered) - 1) * fraction
        lower = math.floor(index)
        upper = math.ceil(index)
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 3)
    return {"samples": len(ordered), "p50_ms": percentile(0.5), "p95_ms": percentile(0.95)}


def summarize_observations(observations: list[dict[str, Any]], dropped: int = 0) -> dict[str, Any]:
    """Build a safe aggregate from validated observations (also used for JSON exports)."""
    counts = {event: 0 for event in EVENT_FIELDS}
    usage = {field: 0.0 for field in RATE_ENV}
    timings: dict[str, list[float]] = {name: [] for name in ("stt_partial", "stt_final", "conversation_response", "tts_first_audio", "avatar_delivery")}
    mapping = {"stt_partial": ("stt_partial", "latency_ms"), "stt": ("stt_final", "latency_ms"), "conversation": ("conversation_response", "latency_ms"), "tts": ("tts_first_audio", "first_audio_ms"), "avatar_delivery": ("avatar_delivery", "latency_ms")}
    required_timings = tuple(timings)
    for event in ("conversation_first_token", "browser_first_frame", "browser_playback", "browser_end_to_end"):
        timings[event] = []
        mapping[event] = (event, "latency_ms")
    for item in observations:
        event = item.get("event")
        metrics = item.get("metrics")
        _validate(event, metrics)
        counts[event] += 1
        if event in mapping:
            name, field = mapping[event]
            if field in metrics:
                timings[name].append(metrics[field])
        for source, target in (("input_tokens", "input_tokens"), ("output_tokens", "output_tokens"), ("characters", "tts_characters"), ("audio_seconds", "audio_seconds"), ("duration_seconds", "avatar_seconds")):
            usage[target] += metrics.get(source, 0)
    costs: dict[str, float | None] = {}
    for field, (env_name, divisor) in RATE_ENV.items():
        raw_rate = os.getenv(env_name)
        try:
            rate = float(raw_rate) if raw_rate is not None else None
        except ValueError:
            rate = None
        costs[field] = usage[field] * rate / divisor if rate is not None and math.isfinite(rate) and rate >= 0 else None
    cycles = min(counts["avatar_start"], counts["avatar_stop"])
    enough = cycles >= 10 and usage["avatar_seconds"] >= 420 and all(timings[name] for name in required_timings) and dropped == 0
    return {
        "schema_version": 2,
        "counts": counts,
        "usage": usage,
        "latency": {name: _percentiles(values) for name, values in timings.items()},
        "cost_usd": {"components": costs, "total": sum(costs.values()) if all(value is not None for value in costs.values()) else None},
        "provider_billing": {"avatar_billable_seconds": None, "stt_billable_seconds": None, "tts_credits": None, "actual_cost_usd": None},
        "dropped_observations": dropped,
        "live_gate": {"observed_start_stop_cycles": cycles, "minimum_cycles": 10, "minimum_avatar_seconds": 420, "minimum_measurements_met": bool(enough), "decision": "MANUAL_REVIEW_REQUIRED" if enough else "INSUFFICIENT_MEASUREMENTS"},
        "limitations": ["Process-local observations expire; restarts discard measurements.", "Conversation response and first-token latency are distinct measurements; missing samples remain null.", "Avatar delivery measures transport completion. Browser first frame and playback do not establish lip synchronization or audible output.", "Configured rates are estimates; provider billing and live quality require manual verification.", "Minimum measurements alone do not establish GO; validate controlled cycle quality, latency and costs."],
    }


def _validate(event: str, metrics: dict[str, Any]) -> None:
    if not isinstance(event, str) or event not in EVENT_FIELDS or not isinstance(metrics, dict):
        raise ValueError("Unsupported metric event")
    if set(metrics) - EVENT_FIELDS[event]:
        raise ValueError("Unsupported metric field")
    for value in metrics.values():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ValueError("Metrics must be finite nonnegative numbers")


class VoicePocMetrics:
    def __init__(self, max_sessions: int = 1024, max_observations: int = 2048, ttl_seconds: int = CONVERSATION_CONTEXT_TTL_SECONDS) -> None:
        if max_observations <= 0 or ttl_seconds <= 0:
            raise ValueError("Metrics bounds and TTL must be positive")
        self._cache = InMemoryConversationCache(max_entries=max_sessions)
        self._lock = threading.RLock()
        self._max_observations = max_observations
        self._ttl_seconds = ttl_seconds

    def record(self, session_id: str, state_id: str, event: str, **metrics: float) -> None:
        _validate(event, metrics)
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128 or not isinstance(state_id, str) or len(state_id) > 128:
            raise ValueError("Invalid metric scope")
        with self._lock:
            payload = self._cache.get(session_id) or {"observations": [], "dropped": 0}
            if len(payload["observations"]) < self._max_observations:
                payload["observations"].append({"state_id": state_id, "event": event, "metrics": metrics})
            else:
                payload["dropped"] += 1
            try:
                self._cache.put(session_id, payload, self._ttl_seconds)
            except RuntimeError:
                # Observability must not interrupt an otherwise successful voice turn.
                return

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            payload = self._cache.get(session_id) or {"observations": [], "dropped": 0}
        return summarize_observations(payload["observations"], payload["dropped"])

    def close(self) -> None:
        self._cache.close()


voice_poc_metrics = VoicePocMetrics()
