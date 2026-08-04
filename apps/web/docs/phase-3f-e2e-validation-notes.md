# Phase 3F E2E Validation Notes

Phase 3F validates the Phase 3 scoring and report chain without adding new product features.

## Tested Chain

Learner answer submission created a mock scoring result through the backend scoring service. The same in-memory snapshot was then read through learner scoring/report endpoints and aggregated through company/platform report endpoints.

## Backend HTTP Results

Real HTTP requests against `uvicorn app.main:app --host 127.0.0.1 --port 8000` verified:

- learner answer submit: `200`
- learner scoring results: `200`
- learner structured report: `200`
- repeated learner report deterministic for the same snapshot
- GET report/scoring reads did not create additional scoring results
- company aggregate with injected `companyId=company-secondary`: `200`, response stayed `company-demo`
- platform aggregate with `companyId=company-demo`: `200`
- invalid date range: `422`
- invalid date format: `422`
- learner role on platform endpoint: `403`
- invalid role: `403`
- missing learner session: `404`
- company/platform aggregate response privacy scan: no `answerText`, `statePrompt`, raw provider, or secret string

## Frontend Results

Mock mode route shell checks against the running Next dev server:

- `/learner/sessions/demo-session-1/report`: `200`
- `/company/reports`: `200`
- `/platform/reports`: `200`

API-mode production shell checks used an API-env build plus `next start --port 3005` with backend running:

- `/learner/sessions/demo-session-1/report`: `200`
- `/company/reports`: `200`
- `/platform/reports`: `200`

The first API-mode browser JavaScript data-fetch attempt could not be visually confirmed because local Chrome exited before opening a CDP port and Edge did not expose the CDP port in headless mode.

Follow-up: Chrome headless with the older `--headless` flag exposed CDP successfully. A production `next start --port 3006` browser pass at `390x844` confirmed the canonical learner, company, and platform report shells hydrate and render role-aware layout. Because the local backend CORS allowlist only includes port `3000`, API-mode report fetches from `127.0.0.1:3006` were blocked by CORS and entered the typed error state.

## Browser And Viewports

Attempted Chrome and Edge headless/CDP automation for desktop, tablet, and mobile viewports.

- Chrome exited with code `-2147483645` before opening `9222`.
- Edge stayed alive in one run but did not expose the remote-debugging port; alternate flags exited with the same code.

No screenshots were captured in the first pass. The follow-up CDP pass at `390x844` verified:

- desktop sidebar is hidden on mobile
- an accessible mobile role navigation button is visible with `aria-label="Open role navigation menu"`
- the mobile menu opens by click/touch, closes with Escape, and stays within the viewport
- platform users see only platform links
- company users see only company links
- learner users see only learner links
- desktop `1280x900` keeps the sidebar visible and hides the mobile menu button

The CDP pass resolved the previous mobile navigation blocker. Manual re-check is still recommended before any future production deployment, but it is no longer a Phase 3F blocker.

## Contract And Adapter Checks

Frontend report adapters match Phase 3D endpoint paths:

- `getLearnerStructuredReport()` -> `/api/learner/sessions/{sessionId}/report`
- `getLearnerSessionScoringResults()` -> `/api/learner/sessions/{sessionId}/scoring-results`
- `getCompanyAggregateReport()` -> `/api/company/reports/aggregate`
- `getPlatformAggregateReport()` -> `/api/platform/reports/aggregate`

Frontend report DTOs align with backend report DTO field names and nullability for the Phase 3C/3D report contracts. Existing non-report template/user DTO differences remain outside the Phase 3F report surface.

The legacy learner route `/learner/report/[sessionId]` was intentionally removed before production. The only supported learner report route is `/learner/sessions/[sessionId]/report`; no redirect or alias remains.

The generic `/report/[sessionId]` learner-report alias was also removed so there is no fallback path to the deleted legacy route.

## Platform Retry Finding

The platform Retry state observed during manual mobile validation was reproduced and traced in browser/CDP.

- Current local frontend env: `NEXT_PUBLIC_DATA_SOURCE_MODE=api`
- API base URL: `http://localhost:8000`
- Platform adapter endpoint: `/api/platform/reports/aggregate`
- Request role header: `x-mock-role: platform`
- Mock fixture path: in `mock` mode, `getPlatformAggregateReport()` returns `mockPlatformAggregateReport` and sends no request
- Runtime exception in the reproduced API-mode case: browser CORS failure
- User-facing error text: `The report service could not be reached.`

Root cause for the reproduced failure: the production frontend test was served from `http://127.0.0.1:3006`, while FastAPI CORS allows `FRONTEND_ORIGIN`, `http://localhost:3000`, and `http://127.0.0.1:3000`. Browser preflight requests from `127.0.0.1:3006` were rejected before the report request could complete. Direct CLI HTTP calls to `http://127.0.0.1:8000/api/platform/reports/aggregate` with `x-mock-role: platform` returned `200`, confirming the backend endpoint itself was healthy.

Conclusion: no report UI success state was forced and no Retry button was hidden. For local API-mode browser validation, run the frontend on port `3000` or configure the backend `FRONTEND_ORIGIN`/CORS allowlist for the actual frontend origin. For mock-mode validation, unset `NEXT_PUBLIC_DATA_SOURCE_MODE=api` or set `NEXT_PUBLIC_DATA_SOURCE_MODE=mock` and rebuild/restart the frontend.

## Learner Answer 429 Finding

The learner answer submit `429` was confirmed as the intentional `max_queries_per_state` guardrail.

- Limit: `MAX_QUERIES_PER_STATE = 3`
- Counter storage: in-memory `scoring_repository._query_counts`
- Counter key: `(session_id, state_id)`
- Increment point: before provider scoring in `scoring_service.score_answer()`
- Clean session validation: `POST /api/learner/sessions` reset to `communication-sales-state-01`; first scored answer returned `200`, included `scoringResult`, and set query count to `1`

Minimum fixes made:

- demo session reset now clears scoring/query state for `demo-session-1`
- demo session reset now clones from the pristine demo fixture instead of a previously mutated active session
- frontend answer submit catches API errors, preserves textarea content, prevents double submit, and shows an inline user-facing message for `max_queries_per_state`

## Fixes Made During Validation

- Added request id guards to report workspaces so stale async responses are ignored after refetch/unmount.
- Added `aria-live` to loading state and `role="alert"` to error state.
- Updated `protectedRoutes` inventory with `/platform/reports` and `/learner/sessions/demo-session-1/report`.
- Added a shared role navigation source for sidebar/topbar and a mobile role navigation menu.
- Preserved the max-queries guardrail while making demo reset clean and handling `429 max_queries_per_state` inline in the learner session UI.

## Commands

- `.venv\Scripts\python.exe -m unittest discover -s tests`
- `.venv\Scripts\python.exe -m unittest tests.test_scoring_service tests.test_report_endpoints`
- `.venv\Scripts\python.exe -m compileall app`
- `npm.cmd run lint`
- `npm.cmd run build`
- API-env `npm.cmd run build`

## Final Validation

Final Phase 3F closing validation passed:

- frontend lint: pass, `0` errors and `3` existing warnings
- frontend build: pass
- backend focused tests: `Ran 36 tests ... OK`
- backend full suite: `Ran 55 tests ... OK`
- canonical report routes present in build: `/learner/sessions/[sessionId]/report`, `/company/reports`, `/platform/reports`
- removed routes absent from build: `/learner/report/[sessionId]`, `/report/[sessionId]`

## Security And Privacy

Scans found no API keys, provider activation, Supabase/Auth activation, debug prints, or console logging in the Phase 3F surface. Matches for sensitive words were documentation/test assertions or existing learner-only answer entry code.

## Decision

Phase 3F decision: `GO`.

Overall Phase 3 status: `COMPLETED`.

The current Phase 3 changes are ready to be reviewed and committed as one coherent Phase 3 commit. No commit or push has been made.
