# Phase 2B-B Supabase Security Foundation Notes

Phase 2B-B hardens the Supabase migration, Auth, RLS, and user-scoped access boundary for the hosted development project. It does not connect real AI, LiveAvatar, STT/TTS providers, or production Supabase.

## Auth Mapping

- `public.users.id` is the application profile id and directly references `auth.users(id)`.
- `public.users.id` uses `on delete cascade`, so deleting the Auth account removes the application profile.
- No separate `auth_user_id` is used; one Auth account maps to at most one application profile.
- The only active application roles are `platform`, `company`, and `learner`.
- Role and tenant decisions must come from trusted `public.users` and `public.company_members` rows, not request payloads, browser storage, client headers, or user-editable metadata.

## Canonical Company Membership

- `company_members` is the canonical tenant membership source.
- `users.company_id` was removed from the database model to avoid two independent tenant sources.
- Platform users must not have active or invited company membership.
- Company and learner users must have exactly one active or invited membership in the MVP.
- Cross-table consistency is enforced with deferrable constraint triggers so controlled provisioning can create the profile and membership in one transaction.
- Membership updates validate both the new and old user ids, so moving a membership cannot leave the previous company or learner user without the required tenant link.

## Provisioning Flow

1. Create or invite the Supabase Auth account through a secure backend/admin path.
2. Insert the matching `public.users` profile server-side with the trusted role.
3. Insert exactly one `company_members` row for company and learner roles.
4. Deny application access when an Auth account has no active trusted profile or, for company/learner roles, no valid membership.

Public self-signup and metadata-driven role/company assignment remain out of scope.

## Schema Constraints

- Primary keys, foreign keys, status checks, role checks, tenant indexes, and `updated_at` triggers are present.
- Enrollment, session, and answer consistency triggers validate tenant and learner ownership paths.
- Report rows remain unique per session.
- Feedback and skill score rows include idempotency-oriented uniqueness for session/state output paths.
- No LiveAvatar transcript table and no raw audio/video storage model were added.

`session_answers` remains in the schema for legacy/model completeness, but Evaluation Contract v2 does not insert raw learner answers in the Supabase finalize path. Final batch scoring persists normalized feedback, scoring, skill impact, usage, report, and evaluation lifecycle metadata without storing raw answer text by default.

## RLS And Grants

- RLS is enabled on product tables with concrete policies.
- `anon` receives no product table access.
- `authenticated` receives only the grants needed for current expected user-scoped read/progress/write paths.
- User profile updates are column-limited to `full_name` and `title`; role and tenant membership cannot be changed through normal user grants.
- Learners can insert their own answers only for sessions they own.
- Company users read tenant data only through `company_members`.
- Platform can manage platform-level resources but is not granted raw learner answer access by default.

## Helper Function Safety

- RLS helpers use `security definer`, stable SQL functions, and `set search_path = public, pg_temp`.
- Helpers resolve identity through `auth.uid()` and trusted public tables.
- Function execute privileges are revoked from `public` and granted only to `authenticated`.
- Helpers do not use `raw_user_meta_data`, request headers, client-supplied company id, or local storage.

## Client Factory Boundary

- `get_supabase_privileged_client()` is explicit and reserved for provisioning, migrations, controlled jobs, or internal operations.
- `get_supabase_user_scoped_client(access_token)` is the future user request boundary and uses a public/publishable key plus the signed-in user token so RLS remains active.
- Ambiguous `get_supabase_client()` now raises in Supabase mode and directs callers to choose the correct boundary.
- Backend privileged key validation supports `SUPABASE_SECRET_KEY` and legacy `SUPABASE_SERVICE_ROLE_KEY`, rejecting conflicting values.
- Frontend must never receive a secret key.
- Real `.env` files remain ignored. `.env.example` files are committed only as secrets-free setup contracts with empty Supabase values; frontend examples currently include only active public runtime variables.

## Seed Idempotency

- Seed uses stable ids and `on conflict`.
- Seed does not delete, truncate, or reset existing data.
- Seed does not insert into `auth.users`.
- App profiles and user-bound rows are inserted only when matching Auth users already exist.
- A second company and second learner fixture are included for future negative tenant tests.

## Hosted Migration Gate

Hosted development migrations `0001` through `0007` are applied on the confirmed Frankfurt development project. The safe bootstrap order for a new development project is:

1. Provision demo Auth users through the Supabase dashboard or a secure admin script, using the stable ids documented in the seed.
2. Apply `0001_initial_schema.sql` to a fresh development database.
3. Apply `0002_rls_policies.sql`.
4. Apply `0003_seed_demo_data.sql`.
5. Apply `0004_fix_membership_consistency_trigger.sql`.
6. Apply `0005_session_evaluation_finalize.sql`.
7. Apply `0006_restrict_finalize_rpc_grants.sql`.
8. Apply `0007_restrict_session_evaluation_table_grants.sql`.
9. Run real Supabase integration tests for platform/company/learner/anon access.
10. Verify health config remains secret-free and mock mode remains default unless the environment intentionally opts into Supabase.

## Integration Test Plan

Credential-free static tests cover schema, RLS, seed, config, finalization, and raw-answer guardrail contracts. Hosted authenticated smoke tests require dedicated E2E credentials supplied outside the repository.

Recommended integration checks:

- platform/company/learner profile mapping through `auth.uid()`
- missing profile denial
- missing company membership denial for company/learner roles
- company A cannot read company B sessions/reports
- learner A cannot read learner B sessions/reports
- learner cannot update role or membership
- anon cannot read product tables
- answer insert tenant spoofing is rejected
- seed second run creates no duplicates

## Decision

Phase 2B-B security foundation: `COMPLETED` for development merge-readiness validation, subject to the final Phase 2B-F dependency and hosted credential gates.
