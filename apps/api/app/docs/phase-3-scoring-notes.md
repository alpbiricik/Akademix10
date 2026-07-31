# Phase 3A/3B Scoring Notes

Phase 3 adds a backend-centered rubric and scoring boundary while keeping mock mode as the default.

## Scope

- Rubrics are versioned and tied to a training template/state.
- Provider requests separate learner answer text from rubric/system scoring data.
- Structured scoring results include rubric version, dimension scores, feedback, skill impacts, guardrail flags, provider metadata, and future token/cost metadata.
- The learner answer endpoint remains backward compatible and now returns `scoringResult` as an additive field.

## Provider Boundary

The default provider is `MockScoringProvider`. It is deterministic, local-only, and does not require API keys. Real OpenAI/Claude adapters can later implement the `ScoringProvider` protocol without changing the scoring service contract.

## Guardrails

- `MAX_QUERIES_PER_STATE = 3`
- Empty and oversized answers are rejected with typed scoring errors.
- Malformed provider output is validated and retried up to the configured retry limit.
- Prompt-injection-like learner text is preserved as answer text and reported through guardrail flags, not executed as scoring instructions.

## Persistence Readiness

`scoring_repository.py` is an in-memory boundary for now. It mirrors the future write path into `session_feedback`, `skill_scores`, cost metadata, and reports without enabling Supabase.
