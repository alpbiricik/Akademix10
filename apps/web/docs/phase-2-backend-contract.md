# Phase 2B Backend Contract Preparation

Phase 2B prepared AkademX10 XAI for a later FastAPI and Supabase backend without replacing the current mock frontend engine. Phase 2G adds concrete Supabase/Postgres migration drafts, seed data, RLS intent, and backend repository skeletons while keeping mock mode as the default.

## Not Implemented Yet

- No real Supabase client connection
- No environment secrets
- No real AI API
- No real LiveAvatar, STT, or TTS integration
- No payment or SSO integration

## Why Contracts First

The Phase 2A frontend uses mock repositories and state-machine data. Phase 2B creates stable names and boundaries before persistence and backend transport are introduced. The goal is to make the future backend replace mock repositories with minimal UI rewrite.

## Role Model

AkademX10 XAI has exactly three roles:

| Role | Scope |
| --- | --- |
| platform | AkademX10 operator. Manages global templates, companies, and assignments. |
| company | Customer company manager. Manages only own employees, enrollments, reports, and usage. |
| learner | Employee learner. Accesses only own assigned trainings, sessions, and reports. |

Platform is not treated as a company admin. Company users cannot access platform routes. Learners cannot access platform or company routes.

## Product Flow

1. Platform creates a global training template.
2. Platform adds modules and state-machine states to the template.
3. Platform assigns templates or modules to a customer company.
4. Company enrolls learners into assigned trainings.
5. Learner starts an assigned session.
6. Session progresses through states and stores answers.
7. Feedback and skill scores are generated.
8. Usage and cost logs are stored for tokens, voice, and LiveAvatar Lite usage.
9. A report is created for the learner session.

## Phase 0 Cost Model

- Total session duration: 40 minutes
- LiveAvatar Lite active target: 7 minutes
- Avatar open/close target: 10
- Buffered billable avatar usage: 8.05 minutes
- Safe total session budget: 1.25 USD

## Future Phases

| Phase | Goal |
| --- | --- |
| Phase 2C | Real backend skeleton with FastAPI. |
| Phase 2G | Supabase/Postgres schema migrations, seed data, RLS draft, and repository skeleton. |
| Phase 3 | AI layer for scoring, feedback, and report generation. |
| Phase 4 | Voice and LiveAvatar Lite proof of concept with usage metering. |

## Phase 2G Database Preparation

- Schema draft created in `supabase/migrations/0001_initial_schema.sql`.
- RLS policy intent created in `supabase/migrations/0002_rls_policies.sql`.
- Deterministic demo seed data created in `supabase/migrations/0003_seed_demo_data.sql`.
- Backend repository skeleton created in `apps/api/app/db/repositories`.
- Default backend database mode remains `mock`.
- Real Supabase credentials, auth mapping, migration apply, and policy testing remain future work.
