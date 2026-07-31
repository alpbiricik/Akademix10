# Phase 3D Report Endpoints Notes

Phase 3D exposes the existing scoring and report services through role-safe HTTP endpoints. It does not add UI integration, real providers, network scoring, Supabase activation, or new roles.

## Endpoints

- `GET /api/learner/sessions/{session_id}/scoring-results`: learner only.
- `GET /api/learner/sessions/{session_id}/report`: learner only.
- `GET /api/company/reports/aggregate`: company only.
- `GET /api/platform/reports/aggregate`: platform only.

Existing learner answer submit remains unchanged and still returns `{ session, feedback, scoringResult }`.

## Identity And Tenant Isolation

Mock identity is resolved from `x-mock-role` using the existing role header pattern:

- `learner` resolves to `user-learner-demo` / `company-demo`.
- `company` resolves to `user-company-demo` / `company-demo`.
- `platform` resolves to `user-platform-demo`.

Learner session access checks `session.userId` against the resolved learner. Company aggregate reports use the server-resolved `company_id`; query/path company id values are not trusted to expand scope. Platform aggregate access is limited to the platform role.

## Generate-On-Read

Report endpoints use generate-on-read over the current in-memory scoring snapshot, then store the generated report through `ReportsRepository`. The output remains deterministic for the same scoring snapshot and report schema version because report timestamps are derived from source scoring timestamps.

GET report endpoints never call the scoring provider and never start a new scoring run.

## Filters

Company aggregate supports:

- `templateId`
- `dateFrom`
- `dateTo`

Platform aggregate supports:

- `templateId`
- `companyId`
- `dateFrom`
- `dateTo`

Date filters must be ISO-8601. `dateFrom > dateTo` returns a 422 typed filter error. Filters never widen the caller's authorization scope.

## Error Contract

Report endpoint errors use FastAPI `HTTPException` with a typed JSON detail:

```json
{ "code": "invalid_report_filter", "message": "dateFrom must be before or equal to dateTo." }
```

Missing or inaccessible learner sessions return a safe not-found error without exposing other tenants.

## Privacy

Aggregate reports do not return learner answer text, prompts, system instructions, raw provider responses, secrets, or raw provider payloads. Provider/cost data is limited to provider/model names and token/cost totals.

## Overall Score Decision

Current 3A/3B code already computes `StructuredScoringResultDTO.overallScore` in `scoring_service.calculate_overall_score()` from provider dimension scores and rubric weights. Phase 3D does not change scoring behavior; report endpoints only aggregate existing scoring results.

## Deferred

- Phase 3E: frontend report UI integration.
- Phase 3F: end-to-end UI/API report validation.
- Real Supabase persistence and real auth remain deferred.
