-- AkademX10 XAI Phase 2G RLS policy draft.
-- This file is intentionally not production-final.
--
-- WARNING:
-- This RLS file is a draft access-control intent document. Do not apply it as
-- production-ready security policy without real Supabase Auth mapping,
-- current_user_role(), current_user_company_id(), platform/company/learner
-- policy tests, and verification that every RLS-enabled table has the correct
-- allow policies. Commented policies below are examples/drafts. If RLS is
-- enabled without final allow policies, access may be blocked. Production RLS
-- must be finalized before real customer data is stored.
--
-- TODO: map auth.uid() to public.users.id once Supabase Auth is wired.
-- TODO: create helper function current_app_user_id().
-- TODO: create helper function current_user_role().
-- TODO: create helper function current_user_company_id().
-- TODO: decide whether app users should be renamed app_users to avoid confusion with auth.users.

alter table users enable row level security;
alter table companies enable row level security;
alter table company_members enable row level security;
alter table training_templates enable row level security;
alter table training_modules enable row level security;
alter table training_states enable row level security;
alter table company_training_assignments enable row level security;
alter table learner_enrollments enable row level security;
alter table training_sessions enable row level security;
alter table session_answers enable row level security;
alter table session_feedback enable row level security;
alter table skill_scores enable row level security;
alter table session_usage enable row level security;
alter table session_cost_logs enable row level security;
alter table session_event_logs enable row level security;
alter table reports enable row level security;

-- Placeholder helper contracts.
-- These are commented out until real auth mapping is implemented.
--
-- create function current_app_user_id() returns uuid stable language sql as $$
--   select id from users where id = auth.uid()
-- $$;
--
-- create function current_user_role() returns text stable language sql as $$
--   select role from users where id = current_app_user_id()
-- $$;
--
-- create function current_user_company_id() returns uuid stable language sql as $$
--   select company_id from users where id = current_app_user_id()
-- $$;

-- Platform intent:
-- Platform users can manage companies, global users, templates, modules, assignments,
-- usage, cost logs, event logs and reports.
--
-- create policy platform_manage_companies on companies
--   for all using (current_user_role() = 'platform')
--   with check (current_user_role() = 'platform');
--
-- create policy platform_manage_templates on training_templates
--   for all using (current_user_role() = 'platform')
--   with check (current_user_role() = 'platform');

-- Company intent:
-- Company users can read/manage only rows scoped to their own company.
--
-- create policy company_read_own_company on companies
--   for select using (id = current_user_company_id() or current_user_role() = 'platform');
--
-- create policy company_read_own_members on company_members
--   for select using (company_id = current_user_company_id() or current_user_role() = 'platform');
--
-- create policy company_read_own_assignments on company_training_assignments
--   for select using (company_id = current_user_company_id() or current_user_role() = 'platform');
--
-- create policy company_manage_own_enrollments on learner_enrollments
--   for all using (company_id = current_user_company_id() or current_user_role() = 'platform')
--   with check (company_id = current_user_company_id() or current_user_role() = 'platform');

-- Learner intent:
-- Learners can read only own enrollments, sessions, answers, feedback, skill scores,
-- session usage summary and reports.
--
-- create policy learner_read_own_enrollments on learner_enrollments
--   for select using (learner_id = current_app_user_id());
--
-- create policy learner_read_own_sessions on training_sessions
--   for select using (learner_id = current_app_user_id());
--
-- create policy learner_write_own_answers on session_answers
--   for insert with check (learner_id = current_app_user_id());
--
-- create policy learner_read_own_answers on session_answers
--   for select using (learner_id = current_app_user_id());
--
-- create policy learner_read_own_feedback on session_feedback
--   for select using (
--     exists (
--       select 1 from training_sessions
--       where training_sessions.id = session_feedback.session_id
--       and training_sessions.learner_id = current_app_user_id()
--     )
--   );

-- Training content visibility intent:
-- Platform can read/manage all templates/modules/states.
-- Company can read templates/modules assigned to its company.
-- Learner can read modules/states for enrolled trainings.
--
-- create policy company_read_assigned_templates on training_templates
--   for select using (
--     current_user_role() = 'platform'
--     or exists (
--       select 1 from company_training_assignments
--       where company_training_assignments.template_id = training_templates.id
--       and company_training_assignments.company_id = current_user_company_id()
--     )
--   );
--
-- create policy learner_read_enrolled_states on training_states
--   for select using (
--     current_user_role() = 'platform'
--     or exists (
--       select 1 from learner_enrollments
--       where learner_enrollments.module_id = training_states.module_id
--       and learner_enrollments.learner_id = current_app_user_id()
--     )
--   );

-- Usage, cost and audit intent:
-- Platform can see all detailed logs.
-- Company can see own company logs.
-- Learners can see their own session_usage summary.
-- Detailed session_cost_logs can stay hidden from learners later if needed.
--
-- create policy learner_read_own_session_usage on session_usage
--   for select using (
--     exists (
--       select 1 from training_sessions
--       where training_sessions.id = session_usage.session_id
--       and training_sessions.learner_id = current_app_user_id()
--     )
--   );
--
-- create policy company_read_own_cost_logs on session_cost_logs
--   for select using (
--     current_user_role() = 'platform'
--     or exists (
--       select 1 from training_sessions
--       where training_sessions.id = session_cost_logs.session_id
--       and training_sessions.company_id = current_user_company_id()
--     )
--   );
--
-- create policy platform_manage_event_logs on session_event_logs
--   for all using (current_user_role() = 'platform')
--   with check (current_user_role() = 'platform');
