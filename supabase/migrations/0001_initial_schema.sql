-- AkademX10 XAI Phase 2B Supabase security foundation schema.
-- Fresh database migration: no production credentials or external services.

create extension if not exists pgcrypto;

create table public.companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  industry text,
  status text not null default 'active' check (status in ('active', 'inactive', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text not null,
  role text not null check (role in ('platform', 'company', 'learner')),
  title text,
  status text not null default 'active' check (status in ('active', 'inactive', 'invited', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.company_members (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role_in_company text not null default 'member',
  status text not null default 'active' check (status in ('active', 'inactive', 'invited', 'archived')),
  created_at timestamptz not null default now(),
  unique(company_id, user_id)
);

create unique index idx_company_members_one_active_user
  on public.company_members(user_id)
  where status in ('active', 'invited');

create table public.training_templates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  category text,
  estimated_duration_min integer not null check (estimated_duration_min > 0),
  default_state_count integer not null check (default_state_count > 0),
  skill_tags text[] not null default '{}',
  status text not null default 'draft' check (status in ('draft', 'active', 'archived')),
  version text not null default '1.0',
  created_by uuid references public.users(id) on delete set null,
  avatar_policy jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.training_modules (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.training_templates(id) on delete cascade,
  title text not null,
  description text,
  duration_min integer not null check (duration_min > 0),
  status text not null default 'draft' check (status in ('draft', 'active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.training_states (
  id uuid primary key default gen_random_uuid(),
  module_id uuid not null references public.training_modules(id) on delete cascade,
  order_index integer not null check (order_index > 0),
  title text not null,
  type text not null check (type in ('intro','video','avatar','question','roleplay','reflection','feedback','final')),
  estimated_min integer not null check (estimated_min >= 0),
  avatar_enabled boolean not null default false,
  avatar_budget_sec integer not null default 0 check (avatar_budget_sec >= 0),
  prompt text not null,
  rubric jsonb not null default '{}'::jsonb,
  skill_tags text[] not null default '{}',
  completion_rule jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(module_id, order_index)
);

create table public.company_training_assignments (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  template_id uuid not null references public.training_templates(id) on delete restrict,
  module_id uuid not null references public.training_modules(id) on delete restrict,
  assigned_by uuid references public.users(id) on delete set null,
  status text not null default 'active' check (status in ('draft', 'active', 'paused', 'completed', 'archived')),
  starts_at timestamptz,
  due_at timestamptz,
  created_at timestamptz not null default now(),
  unique(company_id, module_id)
);

create table public.learner_enrollments (
  id uuid primary key default gen_random_uuid(),
  assignment_id uuid not null references public.company_training_assignments(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  learner_id uuid not null references public.users(id) on delete cascade,
  module_id uuid not null references public.training_modules(id) on delete restrict,
  status text not null default 'not_started' check (status in ('not_started','in_progress','completed','overdue')),
  assigned_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  unique(assignment_id, learner_id)
);

create table public.training_sessions (
  id uuid primary key default gen_random_uuid(),
  enrollment_id uuid references public.learner_enrollments(id) on delete set null,
  module_id uuid not null references public.training_modules(id) on delete restrict,
  template_id uuid not null references public.training_templates(id) on delete restrict,
  learner_id uuid not null references public.users(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  current_state_id uuid references public.training_states(id) on delete set null,
  completed_state_ids uuid[] not null default '{}',
  status text not null default 'not_started' check (status in ('not_started','in_progress','completed')),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table public.session_answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  state_id uuid not null references public.training_states(id) on delete restrict,
  learner_id uuid not null references public.users(id) on delete cascade,
  answer_text text not null,
  answer_type text not null default 'text' check (answer_type in ('text', 'transcript')),
  submitted_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  unique(session_id, state_id, learner_id, submitted_at)
);

create table public.session_feedback (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  state_id uuid not null references public.training_states(id) on delete restrict,
  answer_id uuid references public.session_answers(id) on delete set null,
  overall_score integer check (overall_score between 0 and 100),
  dimensions jsonb not null default '[]'::jsonb,
  feedback_text text,
  improvement_suggestion text,
  next_action text,
  provider text not null default 'mock',
  model_name text,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  unique(session_id, state_id, answer_id)
);

create table public.skill_scores (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  state_id uuid references public.training_states(id) on delete set null,
  learner_id uuid not null references public.users(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  skill text not null,
  score integer not null check (score between 0 and 100),
  delta integer not null default 0,
  source text not null default 'mock',
  created_at timestamptz not null default now(),
  unique(session_id, state_id, skill, source)
);

create table public.session_usage (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.training_sessions(id) on delete cascade,
  total_duration_min numeric not null default 40,
  avatar_target_min numeric not null default 7,
  avatar_used_min numeric not null default 0,
  avatar_open_count integer not null default 0,
  buffered_avatar_min numeric not null default 8.05,
  stt_minutes numeric not null default 0,
  tts_characters integer not null default 0,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  estimated_avatar_cost_usd numeric not null default 0,
  estimated_llm_cost_usd numeric not null default 0,
  estimated_stt_cost_usd numeric not null default 0,
  estimated_tts_cost_usd numeric not null default 0,
  estimated_total_cost_usd numeric not null default 0,
  safe_budget_usd numeric not null default 1.25,
  updated_at timestamptz not null default now()
);

create table public.session_cost_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  state_id uuid references public.training_states(id) on delete set null,
  event_type text not null,
  provider text not null default 'mock',
  model_name text,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  stt_seconds numeric not null default 0,
  tts_characters integer not null default 0,
  avatar_active_seconds numeric not null default 0,
  avatar_open_count integer not null default 0,
  billable_duration_seconds numeric not null default 0,
  estimated_cost_usd numeric not null default 0,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table public.session_event_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  state_id uuid references public.training_states(id) on delete set null,
  user_id uuid references public.users(id) on delete set null,
  event_type text not null check (event_type in ('session_started','state_started','answer_submitted','feedback_generated','avatar_opened','avatar_closed','state_completed','session_completed','cost_logged')),
  event_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.training_sessions(id) on delete cascade,
  learner_id uuid not null references public.users(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  module_id uuid not null references public.training_modules(id) on delete restrict,
  overall_score integer check (overall_score between 0 and 100),
  skill_summary jsonb not null default '[]'::jsonb,
  strengths jsonb not null default '[]'::jsonb,
  improvement_areas jsonb not null default '[]'::jsonb,
  action_plan jsonb not null default '[]'::jsonb,
  generated_by text not null default 'mock',
  generated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create function public.set_updated_at() returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_companies_updated_at before update on public.companies
for each row execute function public.set_updated_at();
create trigger set_users_updated_at before update on public.users
for each row execute function public.set_updated_at();
create trigger set_training_templates_updated_at before update on public.training_templates
for each row execute function public.set_updated_at();
create trigger set_training_modules_updated_at before update on public.training_modules
for each row execute function public.set_updated_at();
create trigger set_training_states_updated_at before update on public.training_states
for each row execute function public.set_updated_at();
create trigger set_training_sessions_updated_at before update on public.training_sessions
for each row execute function public.set_updated_at();
create trigger set_session_usage_updated_at before update on public.session_usage
for each row execute function public.set_updated_at();

create function public.enforce_company_membership_consistency() returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
  target_user_id uuid;
  target_role text;
  active_memberships integer;
begin
  if tg_table_name = 'users' then
    if tg_op in ('INSERT', 'UPDATE') then
      target_user_id = new.id;
    else
      target_user_id = old.id;
    end if;
    select role into target_role from public.users where id = target_user_id;

    if target_role = 'platform' and exists (
      select 1 from public.company_members
      where user_id = target_user_id and status in ('active', 'invited')
    ) then
      raise exception 'Platform users must not have company membership.';
    end if;

    if target_role in ('company', 'learner') then
      select count(*) into active_memberships
      from public.company_members
      where user_id = target_user_id and status in ('active', 'invited');
      if active_memberships <> 1 then
        raise exception 'Company and learner users require exactly one active company membership.';
      end if;
    end if;

    return null;
  end if;

  if tg_op in ('INSERT', 'UPDATE') then
    target_user_id = new.user_id;
    select role into target_role from public.users where id = target_user_id;

    if target_role = 'platform' and exists (
      select 1 from public.company_members
      where user_id = target_user_id and status in ('active', 'invited')
    ) then
      raise exception 'Platform users must not have company membership.';
    end if;

    if target_role in ('company', 'learner') then
      select count(*) into active_memberships
      from public.company_members
      where user_id = target_user_id and status in ('active', 'invited');
      if active_memberships <> 1 then
        raise exception 'Company and learner users require exactly one active company membership.';
      end if;
    end if;
  end if;

  if tg_op in ('UPDATE', 'DELETE') then
    target_user_id = old.user_id;
    select role into target_role from public.users where id = target_user_id;

    if target_role = 'platform' and exists (
      select 1 from public.company_members
      where user_id = target_user_id and status in ('active', 'invited')
    ) then
      raise exception 'Platform users must not have company membership.';
    end if;

    if target_role in ('company', 'learner') then
      select count(*) into active_memberships
      from public.company_members
      where user_id = target_user_id and status in ('active', 'invited');
      if active_memberships <> 1 then
        raise exception 'Company and learner users require exactly one active company membership.';
      end if;
    end if;
  end if;

  return null;
end;
$$;

create constraint trigger company_membership_after_user_change
after insert or update of role, status on public.users
deferrable initially deferred
for each row execute function public.enforce_company_membership_consistency();

create constraint trigger company_membership_after_member_change
after insert or update or delete on public.company_members
deferrable initially deferred
for each row execute function public.enforce_company_membership_consistency();

create function public.enforce_enrollment_consistency() returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1 from public.users
    where id = new.learner_id and role = 'learner' and status = 'active'
  ) then
    raise exception 'Enrollment learner_id must reference an active learner profile.';
  end if;
  if not exists (
    select 1 from public.company_members
    where user_id = new.learner_id and company_id = new.company_id and status = 'active'
  ) then
    raise exception 'Enrollment learner must be an active member of the enrollment company.';
  end if;
  if not exists (
    select 1 from public.company_training_assignments
    where id = new.assignment_id and company_id = new.company_id and module_id = new.module_id
  ) then
    raise exception 'Enrollment must match assignment company and module.';
  end if;
  return new;
end;
$$;

create trigger learner_enrollments_consistency before insert or update on public.learner_enrollments
for each row execute function public.enforce_enrollment_consistency();

create function public.enforce_session_consistency() returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1 from public.company_members
    where user_id = new.learner_id and company_id = new.company_id and status = 'active'
  ) then
    raise exception 'Session learner must be an active member of the session company.';
  end if;
  if new.enrollment_id is not null and not exists (
    select 1 from public.learner_enrollments
    where id = new.enrollment_id
      and learner_id = new.learner_id
      and company_id = new.company_id
      and module_id = new.module_id
  ) then
    raise exception 'Session must match enrollment learner, company and module.';
  end if;
  return new;
end;
$$;

create trigger training_sessions_consistency before insert or update on public.training_sessions
for each row execute function public.enforce_session_consistency();

create function public.enforce_answer_consistency() returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1 from public.training_sessions
    where id = new.session_id and learner_id = new.learner_id
  ) then
    raise exception 'Answer learner must own the session.';
  end if;
  return new;
end;
$$;

create trigger session_answers_consistency before insert or update on public.session_answers
for each row execute function public.enforce_answer_consistency();

create index idx_users_role on public.users(role);
create index idx_company_members_company_user on public.company_members(company_id, user_id);
create index idx_company_members_user_status on public.company_members(user_id, status);
create index idx_training_templates_created_by on public.training_templates(created_by);
create index idx_training_modules_template_id on public.training_modules(template_id);
create index idx_training_states_module_order on public.training_states(module_id, order_index);
create index idx_company_training_assignments_company_id on public.company_training_assignments(company_id);
create index idx_company_training_assignments_template_module on public.company_training_assignments(template_id, module_id);
create index idx_learner_enrollments_company_learner on public.learner_enrollments(company_id, learner_id);
create index idx_learner_enrollments_assignment on public.learner_enrollments(assignment_id);
create index idx_training_sessions_company_learner on public.training_sessions(company_id, learner_id);
create index idx_training_sessions_enrollment on public.training_sessions(enrollment_id);
create index idx_session_answers_session_state on public.session_answers(session_id, state_id);
create index idx_session_answers_learner on public.session_answers(learner_id);
create index idx_session_feedback_session_state on public.session_feedback(session_id, state_id);
create index idx_session_feedback_answer on public.session_feedback(answer_id);
create index idx_skill_scores_session_id on public.skill_scores(session_id);
create index idx_skill_scores_company_learner on public.skill_scores(company_id, learner_id);
create index idx_session_cost_logs_session_id on public.session_cost_logs(session_id);
create index idx_session_event_logs_session_id on public.session_event_logs(session_id);
create index idx_reports_company_learner on public.reports(company_id, learner_id);
