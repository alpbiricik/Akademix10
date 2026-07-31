# Phase 3C Report Generation Notes

Phase 3C adds a deterministic report generation engine over `StructuredScoringResultDTO` snapshots. It does not add new HTTP endpoints, UI integration, real providers, or Supabase activation.

## Report Types

- `learner_session`: one learner session, including score coverage, dimension and skill summaries, strengths, improvement areas, safe next actions, guardrail summary, rubric refs, and provider/cost summary.
- `company_aggregate`: company-scoped aggregate only. It omits raw learner answers, raw provider payloads, and unnecessary individual learner detail.
- `platform_aggregate`: future-ready platform contract for company/template/session counts, aggregate scores, dimension/skill trends, coverage, and provider/cost summary.

## Aggregation Rules

- Scoring results are validated before use.
- Duplicate scoring results are deduplicated by `(sessionId, stateId)`.
- The latest result is selected by `generatedAt`, with `answerRef` as deterministic tie-breaker.
- Aggregate output is sorted by stable ids, so input order does not affect results.
- Session overall score is the average of deduplicated state scores.
- Company/platform overall score is the average of scored session averages.
- Dimension and skill summaries use arithmetic averages across deduplicated scoring results.
- Strongest items sort by descending score, then id/name. Priority items sort by ascending score, then id/name.

## Rounding And Coverage

- Numeric report metrics use two decimal places.
- Empty datasets return safe reports with zero coverage and `averageOverallScore = null`.
- No division-by-zero is allowed.
- `insufficientSample` is true when scored session count is below `INSUFFICIENT_SAMPLE_SESSION_THRESHOLD`.
- Learner reports mark `isPartial` when the session is incomplete or expected states are missing scores.

## Privacy Boundaries

- Learner reports include only development-focused learner/session information.
- Company/platform aggregate reports do not include learner answer text, raw prompts, system instructions, raw provider responses, secrets, or cross-company data.
- Provider/cost metadata is limited to provider/model names and token/cost totals.

## Repository Compatibility

`ReportsRepository` keeps the existing mock `ReportDTO` path and now supports in-memory generated report persistence by report id. This mirrors the future `reports.metadata`, `skill_summary`, `strengths`, `improvement_areas`, and `action_plan` Supabase write path without enabling a database connection.

## Deferred

- Phase 3D: backend report endpoints and role-access checks.
- Phase 3E: frontend report UI integration.
- Phase 3F: end-to-end UI/API report validation.
