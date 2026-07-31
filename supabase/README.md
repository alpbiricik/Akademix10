# AkademX10 XAI Supabase Schema Draft

This folder prepares the Phase 2 database model for a future Supabase/Postgres integration.

## Files

- `migrations/0001_initial_schema.sql`: Postgres schema for B2B SaaS roles, companies, training content, assignments, enrollments, sessions, answers, feedback, scores, usage, cost logs, event logs, and reports.
- `migrations/0002_rls_policies.sql`: draft Supabase RLS intent for platform/company/learner access.
- `migrations/0003_seed_demo_data.sql`: deterministic demo data matching the current mock product flow, including one 21-state customer communication module.

## Current Status

Production-ready:

- Table coverage for the Core MVP domain.
- Foreign key relationships for company, learner, training, session, report, and usage boundaries.
- Cost and audit tables for token/STT/TTS/avatar usage logging.
- Deterministic seed data for local validation later.

Draft/not production-final:

- RLS policies are intentionally commented as intent until real Supabase Auth mapping exists.
- No Supabase credentials are included.
- No production Supabase project is connected.
- No raw audio/video storage is included by default.
- AI, LiveAvatar, STT and TTS providers are not connected.

## Future Supabase CLI Reference

These commands are references for a later phase. Supabase CLI is not required for Phase 2G.

```powershell
supabase init
supabase migration new add_core_mvp_tables
supabase db reset
supabase db push
```

## Data Retention Note

Raw audio/video should not be stored by default. Store text/transcripts, normalized feedback, scores, reports, usage summaries, cost logs, and audit events unless the product explicitly adds consent, retention rules, and secure media storage later.
