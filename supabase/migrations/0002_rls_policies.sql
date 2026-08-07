-- AkademX10 XAI Phase 2B production RLS policy foundation.
-- Auth source is auth.uid(); role and tenant are read only from public.users
-- and public.company_members.

revoke all on schema public from anon;
revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon;
revoke all on all tables in schema public from authenticated;
revoke all on all functions in schema public from authenticated;

grant usage on schema public to authenticated;

create function public.current_app_user_id() returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select u.id
  from public.users u
  where u.id = auth.uid()
    and u.status = 'active'
$$;

create function public.current_app_role() returns text
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select u.role
  from public.users u
  where u.id = auth.uid()
    and u.status = 'active'
$$;

create function public.current_app_company_id() returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select cm.company_id
  from public.company_members cm
  join public.users u on u.id = cm.user_id
  where cm.user_id = auth.uid()
    and cm.status = 'active'
    and u.status = 'active'
    and u.role in ('company', 'learner')
  limit 1
$$;

create function public.is_platform_user() returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select public.current_app_role() = 'platform'
$$;

create function public.is_company_member(target_company_id uuid) returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1
    from public.company_members cm
    join public.users u on u.id = cm.user_id
    where cm.company_id = target_company_id
      and cm.user_id = auth.uid()
      and cm.status = 'active'
      and u.status = 'active'
      and u.role in ('company', 'learner')
  )
$$;

create function public.is_company_user_for(target_company_id uuid) returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select public.current_app_role() = 'company'
    and public.is_company_member(target_company_id)
$$;

create function public.is_learner_user_for(target_learner_id uuid) returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select auth.uid() = target_learner_id
    and public.current_app_role() = 'learner'
$$;

create function public.can_read_user(target_user_id uuid) returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select public.is_platform_user()
    or auth.uid() = target_user_id
    or exists (
      select 1
      from public.company_members viewer
      join public.company_members target on target.company_id = viewer.company_id
      where viewer.user_id = auth.uid()
        and target.user_id = target_user_id
        and viewer.status = 'active'
        and target.status = 'active'
        and public.current_app_role() = 'company'
    )
$$;

create function public.session_company_id(target_session_id uuid) returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select ts.company_id from public.training_sessions ts where ts.id = target_session_id
$$;

create function public.session_learner_id(target_session_id uuid) returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select ts.learner_id from public.training_sessions ts where ts.id = target_session_id
$$;

create function public.can_read_session(target_session_id uuid) returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select public.is_platform_user()
    or public.is_company_user_for(public.session_company_id(target_session_id))
    or public.is_learner_user_for(public.session_learner_id(target_session_id))
$$;

revoke all on function public.current_app_user_id() from public;
revoke all on function public.current_app_role() from public;
revoke all on function public.current_app_company_id() from public;
revoke all on function public.is_platform_user() from public;
revoke all on function public.is_company_member(uuid) from public;
revoke all on function public.is_company_user_for(uuid) from public;
revoke all on function public.is_learner_user_for(uuid) from public;
revoke all on function public.can_read_user(uuid) from public;
revoke all on function public.session_company_id(uuid) from public;
revoke all on function public.session_learner_id(uuid) from public;
revoke all on function public.can_read_session(uuid) from public;

grant execute on function public.current_app_user_id() to authenticated;
grant execute on function public.current_app_role() to authenticated;
grant execute on function public.current_app_company_id() to authenticated;
grant execute on function public.is_platform_user() to authenticated;
grant execute on function public.is_company_member(uuid) to authenticated;
grant execute on function public.is_company_user_for(uuid) to authenticated;
grant execute on function public.is_learner_user_for(uuid) to authenticated;
grant execute on function public.can_read_user(uuid) to authenticated;
grant execute on function public.session_company_id(uuid) to authenticated;
grant execute on function public.session_learner_id(uuid) to authenticated;
grant execute on function public.can_read_session(uuid) to authenticated;

alter table public.users enable row level security;
alter table public.companies enable row level security;
alter table public.company_members enable row level security;
alter table public.training_templates enable row level security;
alter table public.training_modules enable row level security;
alter table public.training_states enable row level security;
alter table public.company_training_assignments enable row level security;
alter table public.learner_enrollments enable row level security;
alter table public.training_sessions enable row level security;
alter table public.session_answers enable row level security;
alter table public.session_feedback enable row level security;
alter table public.skill_scores enable row level security;
alter table public.session_usage enable row level security;
alter table public.session_cost_logs enable row level security;
alter table public.session_event_logs enable row level security;
alter table public.reports enable row level security;

grant select on public.companies, public.users, public.company_members, public.training_templates,
  public.training_modules, public.training_states, public.company_training_assignments,
  public.learner_enrollments, public.training_sessions, public.session_answers,
  public.session_feedback, public.skill_scores, public.session_usage, public.reports
  to authenticated;
grant insert on public.session_answers, public.session_event_logs to authenticated;
grant update(full_name, title) on public.users to authenticated;
grant update(completed_state_ids, current_state_id, status, completed_at, metadata) on public.training_sessions to authenticated;
grant update(status, started_at, completed_at) on public.learner_enrollments to authenticated;

create policy platform_all_companies on public.companies
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy member_read_own_company on public.companies
  for select using (public.is_company_member(id));

create policy read_visible_users on public.users
  for select using (public.can_read_user(id));
create policy self_update_profile_text on public.users
  for update using (id = auth.uid()) with check (id = auth.uid());

create policy platform_manage_company_members on public.company_members
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy company_read_own_members on public.company_members
  for select using (public.is_platform_user() or public.is_company_member(company_id));

create policy platform_manage_templates on public.training_templates
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy tenant_read_assigned_templates on public.training_templates
  for select using (
    public.is_platform_user()
    or exists (
      select 1 from public.company_training_assignments cta
      where cta.template_id = training_templates.id
        and public.is_company_member(cta.company_id)
    )
  );

create policy platform_manage_modules on public.training_modules
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy tenant_read_assigned_modules on public.training_modules
  for select using (
    public.is_platform_user()
    or exists (
      select 1 from public.company_training_assignments cta
      where cta.module_id = training_modules.id
        and public.is_company_member(cta.company_id)
    )
    or exists (
      select 1 from public.learner_enrollments le
      where le.module_id = training_modules.id
        and le.learner_id = auth.uid()
    )
  );

create policy platform_manage_states on public.training_states
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy tenant_read_enrolled_or_assigned_states on public.training_states
  for select using (
    public.is_platform_user()
    or exists (
      select 1 from public.company_training_assignments cta
      where cta.module_id = training_states.module_id
        and public.is_company_member(cta.company_id)
    )
    or exists (
      select 1 from public.learner_enrollments le
      where le.module_id = training_states.module_id
        and le.learner_id = auth.uid()
    )
  );

create policy platform_manage_assignments on public.company_training_assignments
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy company_read_own_assignments on public.company_training_assignments
  for select using (public.is_company_user_for(company_id));

create policy platform_manage_enrollments on public.learner_enrollments
  for all using (public.is_platform_user()) with check (public.is_platform_user());
create policy company_read_own_enrollments on public.learner_enrollments
  for select using (public.is_company_user_for(company_id));
create policy learner_read_own_enrollments on public.learner_enrollments
  for select using (public.is_learner_user_for(learner_id));
create policy learner_update_own_enrollment_progress on public.learner_enrollments
  for update using (public.is_learner_user_for(learner_id)) with check (public.is_learner_user_for(learner_id));

create policy platform_read_sessions on public.training_sessions
  for select using (public.is_platform_user());
create policy company_read_own_sessions on public.training_sessions
  for select using (public.is_company_user_for(company_id));
create policy learner_read_own_sessions on public.training_sessions
  for select using (public.is_learner_user_for(learner_id));
create policy learner_update_own_session_progress on public.training_sessions
  for update using (public.is_learner_user_for(learner_id)) with check (public.is_learner_user_for(learner_id));

create policy company_read_own_answers on public.session_answers
  for select using (public.is_company_user_for(public.session_company_id(session_id)));
create policy learner_read_own_answers on public.session_answers
  for select using (public.is_learner_user_for(learner_id));
create policy learner_insert_own_answers on public.session_answers
  for insert with check (
    public.is_learner_user_for(learner_id)
    and public.session_learner_id(session_id) = auth.uid()
  );

create policy read_visible_feedback on public.session_feedback
  for select using (public.can_read_session(session_id));
create policy read_visible_skill_scores on public.skill_scores
  for select using (
    public.is_platform_user()
    or public.is_company_user_for(company_id)
    or public.is_learner_user_for(learner_id)
  );
create policy read_visible_usage on public.session_usage
  for select using (public.can_read_session(session_id));
create policy company_read_own_cost_logs on public.session_cost_logs
  for select using (
    public.is_platform_user()
    or public.is_company_user_for(public.session_company_id(session_id))
  );
create policy read_visible_event_logs on public.session_event_logs
  for select using (
    public.is_platform_user()
    or public.is_company_user_for(public.session_company_id(session_id))
    or user_id = auth.uid()
  );
create policy learner_insert_own_event_logs on public.session_event_logs
  for insert with check (
    user_id = auth.uid()
    and public.can_read_session(session_id)
  );

create policy read_visible_reports on public.reports
  for select using (
    public.is_platform_user()
    or public.is_company_user_for(company_id)
    or public.is_learner_user_for(learner_id)
  );
