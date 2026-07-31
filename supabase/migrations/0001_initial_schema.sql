-- AkademX10 XAI Phase 2G initial Postgres schema draft.
-- No production credentials or external services are configured by this migration.

create extension if not exists pgcrypto;

create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  industry text,
  status text not null default 'active' check (status in ('active', 'inactive', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  full_name text not null,
  role text not null check (role in ('platform', 'company', 'learner')),
  title text,
  company_id uuid references companies(id) on delete set null,
  status text not null default 'active' check (status in ('active', 'inactive', 'invited', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table company_members (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role_in_company text not null default 'member',
  status text not null default 'active' check (status in ('active', 'inactive', 'invited', 'archived')),
  created_at timestamptz not null default now(),
  unique(company_id, user_id)
);

create table training_templates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  category text,
  estimated_duration_min integer not null check (estimated_duration_min > 0),
  default_state_count integer not null check (default_state_count > 0),
  skill_tags text[] not null default '{}',
  status text not null default 'draft' check (status in ('draft', 'active', 'archived')),
  version text not null default '1.0',
  created_by uuid references users(id) on delete set null,
  avatar_policy jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table training_modules (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references training_templates(id) on delete cascade,
  title text not null,
  description text,
  duration_min integer not null check (duration_min > 0),
  status text not null default 'draft' check (status in ('draft', 'active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table training_states (
  id uuid primary key default gen_random_uuid(),
  module_id uuid not null references training_modules(id) on delete cascade,
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

create table company_training_assignments (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  template_id uuid not null references training_templates(id) on delete restrict,
  module_id uuid not null references training_modules(id) on delete restrict,
  assigned_by uuid references users(id) on delete set null,
  status text not null default 'active' check (status in ('draft', 'active', 'paused', 'completed', 'archived')),
  starts_at timestamptz,
  due_at timestamptz,
  created_at timestamptz not null default now()
);

create table learner_enrollments (
  id uuid primary key default gen_random_uuid(),
  assignment_id uuid not null references company_training_assignments(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  learner_id uuid not null references users(id) on delete cascade,
  module_id uuid not null references training_modules(id) on delete restrict,
  status text not null default 'not_started' check (status in ('not_started','in_progress','completed','overdue')),
  assigned_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  unique(assignment_id, learner_id)
);

create table training_sessions (
  id uuid primary key default gen_random_uuid(),
  enrollment_id uuid references learner_enrollments(id) on delete set null,
  module_id uuid not null references training_modules(id) on delete restrict,
  template_id uuid not null references training_templates(id) on delete restrict,
  learner_id uuid not null references users(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  current_state_id uuid references training_states(id) on delete set null,
  completed_state_ids uuid[] not null default '{}',
  status text not null default 'not_started' check (status in ('not_started','in_progress','completed')),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table session_answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references training_sessions(id) on delete cascade,
  state_id uuid not null references training_states(id) on delete restrict,
  learner_id uuid not null references users(id) on delete cascade,
  answer_text text not null,
  answer_type text not null default 'text' check (answer_type in ('text', 'transcript')),
  submitted_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table session_feedback (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references training_sessions(id) on delete cascade,
  state_id uuid not null references training_states(id) on delete restrict,
  answer_id uuid references session_answers(id) on delete set null,
  overall_score integer check (overall_score between 0 and 100),
  dimensions jsonb not null default '[]'::jsonb,
  feedback_text text,
  improvement_suggestion text,
  next_action text,
  provider text not null default 'mock',
  model_name text,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table skill_scores (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references training_sessions(id) on delete cascade,
  state_id uuid references training_states(id) on delete set null,
  learner_id uuid not null references users(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  skill text not null,
  score integer not null check (score between 0 and 100),
  delta integer not null default 0,
  source text not null default 'mock',
  created_at timestamptz not null default now()
);

create table session_usage (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references training_sessions(id) on delete cascade,
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

create table session_cost_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references training_sessions(id) on delete cascade,
  state_id uuid references training_states(id) on delete set null,
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

create table session_event_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references training_sessions(id) on delete cascade,
  state_id uuid references training_states(id) on delete set null,
  user_id uuid references users(id) on delete set null,
  event_type text not null check (event_type in ('session_started','state_started','answer_submitted','feedback_generated','avatar_opened','avatar_closed','state_completed','session_completed','cost_logged')),
  event_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references training_sessions(id) on delete cascade,
  learner_id uuid not null references users(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  module_id uuid not null references training_modules(id) on delete restrict,
  overall_score integer check (overall_score between 0 and 100),
  skill_summary jsonb not null default '[]'::jsonb,
  strengths jsonb not null default '[]'::jsonb,
  improvement_areas jsonb not null default '[]'::jsonb,
  action_plan jsonb not null default '[]'::jsonb,
  generated_by text not null default 'mock',
  generated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index idx_users_role on users(role);
create index idx_users_company_id on users(company_id);
create index idx_training_states_module_order on training_states(module_id, order_index);
create index idx_company_training_assignments_company_id on company_training_assignments(company_id);
create index idx_learner_enrollments_company_learner on learner_enrollments(company_id, learner_id);
create index idx_training_sessions_company_learner on training_sessions(company_id, learner_id);
create index idx_session_answers_session_id on session_answers(session_id);
create index idx_session_feedback_session_id on session_feedback(session_id);
create index idx_skill_scores_session_id on skill_scores(session_id);
create index idx_session_cost_logs_session_id on session_cost_logs(session_id);
create index idx_session_event_logs_session_id on session_event_logs(session_id);
