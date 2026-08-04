# Phase 3E Report UI Notes

Phase 3E connects the Phase 3D role-safe report endpoints to role-scoped frontend report screens. It does not add report export, new scoring logic, real providers, Supabase/Auth, or broad dashboard redesign.

## Routes

- Learner: `/learner/sessions/[sessionId]/report`
- Company: `/company/reports`
- Platform: `/platform/reports`

## Adapter And Endpoint Mapping

- Learner UI uses `getLearnerStructuredReport()` and `getLearnerSessionScoringResults()`.
- Company UI uses `getCompanyAggregateReport()`.
- Platform UI uses `getPlatformAggregateReport()`.

No component performs direct fetch calls. The UI displays backend-provided overall scores, averages, and coverage without recalculating them.

## UI States

Each report workspace supports loading, retry, empty data, partial coverage, insufficient sample, typed 403/404/filter errors, and generic network/server errors. Backend error payloads are mapped to user-facing copy without rendering stack traces or raw JSON.

## Filters

Company supports `templateId`, `dateFrom`, and `dateTo`.
Platform supports `templateId`, `companyId`, `dateFrom`, and `dateTo`.
Date range validation blocks `dateFrom > dateTo` before sending a request.

## Privacy

Company and platform aggregate screens render only aggregate DTO fields. They do not render learner responses, prompts, system instructions, raw provider payloads, or secrets. Company UI does not expose a company-id authorization input.

## Mock/API Mode

API mode calls Phase 3D endpoints through role-specific adapters. Mock mode uses deterministic DTO-shaped fixtures so report screens stay usable without a backend. The learner report UI supports only `/learner/sessions/[sessionId]/report`; no legacy learner report route or alias remains.

## Manual UI Validation

Run the frontend and check the learner, company, and platform report routes at desktop and narrow widths. Phase 3F will cover full end-to-end UI/API validation.
