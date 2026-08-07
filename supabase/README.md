# AkademX10 XAI Supabase Security Foundation

This folder contains the Phase 2B Supabase/Postgres development schema, RLS, demo seed, and evaluation-finalization migrations. It is a development merge-readiness artifact, not a production or compliance sign-off.

## Files

- `migrations/0001_initial_schema.sql`: Postgres schema for B2B SaaS roles, canonical company membership, training content, assignments, enrollments, sessions, answers, feedback, scores, usage, cost logs, event logs, and reports.
- `migrations/0002_rls_policies.sql`: Supabase RLS foundation for platform/company/learner access using `auth.uid()` and trusted profile/membership rows.
- `migrations/0003_seed_demo_data.sql`: idempotent deterministic demo data matching the current mock product flow, including one 21-state customer communication module and a second tenant fixture.
- `migrations/0004_fix_membership_consistency_trigger.sql`: forward fix for the user/company membership consistency trigger.
- `migrations/0005_session_evaluation_finalize.sql`: evaluation lifecycle table plus atomic finalize RPC for Contract v2.
- `migrations/0006_restrict_finalize_rpc_grants.sql`: restricts finalize RPC execution to authenticated users.
- `migrations/0007_restrict_session_evaluation_table_grants.sql`: removes anon table privileges from the evaluation lifecycle table.

## Current Status

Development-ready:

- Table coverage for the Core MVP domain.
- Direct `public.users.id` to `auth.users.id` mapping.
- Canonical tenant membership through `company_members`.
- Foreign key relationships for company, learner, training, session, report, and usage boundaries.
- RLS helpers, grants, and concrete policies for platform/company/learner/anon scopes.
- Cost and audit tables for token/STT/TTS/avatar usage logging.
- Idempotent deterministic seed data for local validation later.
- Hosted development project is linked and uses the Frankfurt region.
- Evaluation Contract v2 persists normalized feedback, scoring, skill impact, usage, and report data without storing raw learner answers by default.

Not production-final:

- No Supabase credentials are included in the repository.
- No production Supabase project should be targeted from this branch.
- Hosted authenticated smoke tests require dedicated E2E credentials supplied outside the repository.
- No raw audio/video storage is included by default.
- AI, LiveAvatar, STT and TTS providers are not connected.

## Supabase CLI Reference

Use only against local or confirmed hosted development projects. Do not run reset, truncate, drop, or production writes from this branch.

```powershell
supabase init
supabase migration new add_core_mvp_tables
supabase db push
```

## Data Retention Note

Raw learner answers, transcripts, audio, and video should not be stored by default. Store normalized feedback, scores, reports, usage summaries, cost logs, and audit events unless the product explicitly adds consent, retention rules, and secure media storage later.
