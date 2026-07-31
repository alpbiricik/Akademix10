# Database Readiness Checklist

## Phase 2G Complete

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
- RLS intent draft exists.
- Deterministic demo seed exists.
- Backend repository skeleton exists.

## Not Connected Yet

- No real Supabase project is connected.
- No real credentials are included.
- No real auth provider mapping exists.
- Production Supabase connection and final RLS policies are pending.
- FastAPI still uses mock data by default.
- Frontend mock mode remains independent of the database.

## Remaining Before Production

- Create the real Supabase project.
- Add secret-managed env vars.
- Decide final auth-to-users mapping.
- Convert RLS draft into tested production policies.
- Apply migrations in a controlled environment.
- Validate seed/reset flow.
- Add backup and retention policy.
- Harden audit/event log access.
- Define data retention for transcripts and reports.
- Keep raw audio/video disabled by default unless explicit consent and secure media storage are added.
