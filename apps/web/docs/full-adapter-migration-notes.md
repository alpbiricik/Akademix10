# Full Frontend Adapter Migration Notes

Phase 2E moved the frontend surface to the adapter layer while keeping mock mode as the default.

## Data Source Boundary

- Pages and role components now call `src/lib/adapters/*`.
- Mock repositories remain behind adapters only.
- `NEXT_PUBLIC_DATA_SOURCE_MODE` still defaults to `mock`.
- API mode is available through the existing adapter configuration, but this phase does not force it.

## Migrated Areas

- Platform pages use `platformAdapter` and `usageAdapter`.
- Company pages use `companyAdapter` and `usageAdapter`.
- Learner pages use `learnerAdapter` and `sessionAdapter`.
- The session runner uses `sessionAdapter` for session load, answer submit, state completion, navigation, and reset.

## Preserved Mock Behavior

- The 21-state training flow remains intact.
- Textarea answers, generated mock feedback, skill impact, previous/next/complete controls, reset, progress, and avatar cost panels remain visible.
- Browser `localStorage` persistence remains active in mock mode for demo sessions and browser-side platform assignments.

## Legacy Routes

The canonical routes are role-scoped:

- `/platform/dashboard`
- `/company/dashboard`
- `/learner/dashboard`
- `/learner/session/[sessionId]`
- `/learner/report/[sessionId]`

Legacy/deprecated redirects are restored for compatibility:

- `/dashboard`
- `/admin`
- `/trainer`
- `/platform`
- `/company`
- `/session/[sessionId]`
- `/report/[sessionId]`
