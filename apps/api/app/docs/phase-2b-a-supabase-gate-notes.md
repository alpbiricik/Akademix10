# Phase 2B-A Supabase Gate Notes

Phase 2B-A adds a safe Supabase connection gate without moving repositories away from mock/in-memory storage.

## Configuration Approach

- Backend database mode is selected with `DATABASE_MODE`.
- Supported backend modes are `mock` and `supabase`.
- Mock mode remains the default and does not require Supabase credentials.
- Supabase mode validates required server-side credentials and does not silently fall back to mock.
- Supabase client creation is centralized in `app/db/database.py`.
- Repository integration is intentionally deferred.

## Environment Variables

Backend placeholders live in `apps/api/.env.example`:

- `DATABASE_MODE`: `mock` or `supabase`
- `SUPABASE_URL`: server-side Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: server-side service role key, never exposed to frontend
- `FRONTEND_ORIGIN`: CORS origin for browser API mode

Frontend placeholders live in `apps/web/.env.example`:

- `NEXT_PUBLIC_DATA_SOURCE_MODE`: frontend adapter mode
- `NEXT_PUBLIC_API_BASE_URL`: FastAPI base URL for API mode
- `NEXT_PUBLIC_SUPABASE_URL`: public Supabase browser URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: public anon/publishable key only

`apps/api/.gitignore` and `apps/web/.gitignore` both ignore `.env*`, so real credentials stay out of git.

## Health Check

`GET /health/config` returns a secret-free configuration status:

- mock mode: `database.status = ok`, `database.databaseMode = mock`
- Supabase mode with missing credentials: `database.status = configuration_error`
- Supabase mode with credentials present: `database.status = ok`, without returning URL or keys

## Migration Static Audit

Migration order is present:

1. `supabase/migrations/0001_initial_schema.sql`
2. `supabase/migrations/0002_rls_policies.sql`
3. `supabase/migrations/0003_seed_demo_data.sql`

Schema strengths:

- active app roles are constrained to `platform`, `company`, and `learner`
- core company, membership, training, enrollment, session, answer, feedback, usage, cost, event, and report tables exist
- foreign keys and cascade/restrict behavior are broadly represented
- no raw audio/video storage table is present

Risks before hosted Supabase apply:

- `users.id` is not yet mapped to `auth.users.id`
- role and company context must be resolved server-side or through trusted DB helpers, not client payloads
- platform users rely on nullable `company_id`; add explicit role/company consistency constraints before production
- company and learner users should require a company relation through checked constraints or tested triggers
- RLS file enables RLS but production allow policies are still draft/commented
- helper functions such as `current_app_user_id()`, `current_user_role()`, and `current_user_company_id()` are not implemented
- seed data uses plain `insert` statements and is not safely re-runnable
- initial schema uses normal `create table` statements, so migrations should be applied once in order, not treated as repeatable scripts

## Manual Supabase Panel Steps

Before applying migrations to a hosted project:

- create or select the Supabase project
- collect project URL, anon/publishable key, and service role key
- store backend service role key only in server-side secret management
- configure frontend with only public URL and anon/publishable key
- decide final `auth.users` to app profile mapping
- convert RLS intent into real helper functions and tested policies
- make seed scripts idempotent or run them only in controlled demo environments
- apply migrations in order in a non-production environment first

## Next Phase 2B Block

Recommended next block: Supabase Auth mapping and production RLS hardening. Do not start repository migration until role/company ownership is enforced and tested.

## Decision

Phase 2B-A: `COMPLETED`.

Overall Phase 2B remains open. Hosted migration apply, Auth mapping, RLS hardening, and repository migration are still blocked on project credentials and security decisions.
