# Database Readiness Checklist

## Phase 2B-B Complete

- Phase 2 database preparation is complete as a draft.
- Core SaaS tables drafted.
- Platform/company/learner role boundaries represented.
- Active app roles are only platform, company, and learner.
- Company membership model included.
- `company_members.role_in_company` is company-internal metadata, not the app UserRole.
- Training templates, modules and ordered states included.
- Company assignments and learner enrollments included.
- Training sessions, answers, feedback and skill scores included.
- Session usage summary included.
- Fine-grained cost logs included.
- Session audit/event logs included.
- Reports table included.
- Production RLS foundation policies exist for platform/company/learner/anon scopes.
- Deterministic demo seed is idempotent and does not create Auth users.
- Backend repository skeleton exists.
- `public.users.id` maps directly to `auth.users.id`.
- `company_members` is the canonical tenant membership source.

## Not Connected Yet

- No real Supabase project is connected.
- No real credentials are included.
- Real auth provider mapping is modeled in the schema but not connected to the app runtime.
- Production Supabase connection is pending.
- FastAPI still uses mock data by default.
- Frontend mock mode remains independent of the database.

## Remaining Before Production

- Create the real Supabase project.
- Add secret-managed env vars.
- Provision demo Auth users through a secure admin path before applying user-bound seed rows.
- Apply migrations in a controlled environment.
- Validate idempotent seed flow.
- Add backup and retention policy.
- Harden audit/event log access.
- Define data retention for transcripts and reports.
- Keep raw audio/video disabled by default unless explicit consent and secure media storage are added.
