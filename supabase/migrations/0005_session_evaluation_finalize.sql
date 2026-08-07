-- Phase 2B-E evaluation lifecycle and atomic finalize persistence.

create table public.session_evaluations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.training_sessions(id) on delete cascade,
  learner_id uuid not null references public.users(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  idempotency_key text not null,
  payload_fingerprint text not null,
  contract_version text not null,
  status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
  attempt_count integer not null default 0,
  failure_code text,
  result_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  updated_at timestamptz not null default now(),
  unique(session_id, idempotency_key)
);

create unique index idx_session_evaluations_completed_session
  on public.session_evaluations(session_id)
  where status = 'completed';

create unique index idx_session_feedback_one_final_per_state
  on public.session_feedback(session_id, state_id)
  where answer_id is null;

create trigger set_session_evaluations_updated_at before update on public.session_evaluations
for each row execute function public.set_updated_at();

create function public.finalize_session_evaluation(
  p_session_id uuid,
  p_idempotency_key text,
  p_payload_fingerprint text,
  p_contract_version text,
  p_results jsonb,
  p_report jsonb,
  p_usage jsonb
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  session_row public.training_sessions%rowtype;
  evaluation_row public.session_evaluations%rowtype;
  result_item jsonb;
  impact_item jsonb;
  dimension_item jsonb;
  dimensions jsonb;
begin
  select * into session_row
  from public.training_sessions
  where id = p_session_id
  for update;

  if not found or session_row.learner_id <> auth.uid() then
    raise exception 'Session not found.';
  end if;

  if not exists (
    select 1
    from public.learner_enrollments le
    where le.id = session_row.enrollment_id
      and le.learner_id = session_row.learner_id
      and le.company_id = session_row.company_id
      and le.status in ('not_started', 'in_progress', 'completed')
  ) then
    raise exception 'Session enrollment is not active.';
  end if;

  select * into evaluation_row
  from public.session_evaluations
  where session_id = p_session_id
    and idempotency_key = p_idempotency_key
  for update;

  if found then
    if evaluation_row.payload_fingerprint <> p_payload_fingerprint then
      raise exception 'Idempotency key payload conflict.';
    end if;
    if evaluation_row.status = 'completed' then
      return jsonb_build_object('status', 'completed', 'evaluationId', evaluation_row.id);
    end if;
  else
    if exists (
      select 1 from public.session_evaluations
      where session_id = p_session_id and status = 'completed'
    ) then
      raise exception 'Session evaluation is already completed.';
    end if;

    insert into public.session_evaluations (
      session_id,
      learner_id,
      company_id,
      idempotency_key,
      payload_fingerprint,
      contract_version,
      status,
      attempt_count,
      started_at
    ) values (
      p_session_id,
      session_row.learner_id,
      session_row.company_id,
      p_idempotency_key,
      p_payload_fingerprint,
      p_contract_version,
      'processing',
      1,
      now()
    )
    returning * into evaluation_row;
  end if;

  for result_item in select * from jsonb_array_elements(p_results)
  loop
    dimensions = '[]'::jsonb;
    for dimension_item in select * from jsonb_array_elements(coalesce(result_item->'dimensionScores', '[]'::jsonb))
    loop
      dimensions = dimensions || jsonb_build_object(
        'label', dimension_item->>'name',
        'score', ((dimension_item->>'score')::numeric)::integer
      );
    end loop;

    insert into public.session_feedback (
      session_id,
      state_id,
      answer_id,
      overall_score,
      dimensions,
      feedback_text,
      improvement_suggestion,
      next_action,
      provider,
      model_name,
      metadata
    ) values (
      p_session_id,
      (result_item->>'stateId')::uuid,
      null,
      (result_item->>'overallScore')::integer,
      dimensions,
      result_item->>'conciseLearnerFeedback',
      coalesce((result_item->'improvementAreas')->>0, ''),
      result_item->>'recommendedNextAction',
      coalesce(result_item->'providerMetadata'->>'provider', 'mock'),
      result_item->'providerMetadata'->>'model',
      jsonb_build_object(
        'schemaVersion', result_item->>'schemaVersion',
        'rubricId', result_item->>'rubricId',
        'rubricVersion', result_item->>'rubricVersion',
        'guardrailFlags', coalesce(result_item->'guardrailFlags', '[]'::jsonb)
      )
    )
    on conflict (session_id, state_id) where answer_id is null do update set
      overall_score = excluded.overall_score,
      dimensions = excluded.dimensions,
      feedback_text = excluded.feedback_text,
      improvement_suggestion = excluded.improvement_suggestion,
      next_action = excluded.next_action,
      provider = excluded.provider,
      model_name = excluded.model_name,
      metadata = excluded.metadata;

    for impact_item in select * from jsonb_array_elements(coalesce(result_item->'skillImpacts', '[]'::jsonb))
    loop
      insert into public.skill_scores (
        session_id,
        state_id,
        learner_id,
        company_id,
        skill,
        score,
        delta,
        source
      ) values (
        p_session_id,
        (result_item->>'stateId')::uuid,
        session_row.learner_id,
        session_row.company_id,
        impact_item->>'skill',
        coalesce((impact_item->>'score')::integer, 0),
        coalesce((impact_item->>'delta')::integer, 0),
        'evaluation-v2'
      )
      on conflict (session_id, state_id, skill, source) do update set
        score = excluded.score,
        delta = excluded.delta;
    end loop;
  end loop;

  insert into public.session_usage (
    session_id,
    total_duration_min,
    avatar_target_min,
    avatar_used_min,
    avatar_open_count,
    buffered_avatar_min,
    input_tokens,
    output_tokens,
    estimated_llm_cost_usd,
    estimated_total_cost_usd,
    safe_budget_usd
  ) values (
    p_session_id,
    coalesce((p_usage->>'totalDurationMin')::numeric, 40),
    coalesce((p_usage->>'avatarTargetMin')::numeric, 7),
    coalesce((p_usage->>'avatarUsedMin')::numeric, 0),
    coalesce((p_usage->>'avatarOpenCount')::integer, 0),
    coalesce((p_usage->>'bufferedAvatarMin')::numeric, 8.05),
    coalesce((p_usage->>'inputTokens')::integer, 0),
    coalesce((p_usage->>'outputTokens')::integer, 0),
    coalesce((p_usage->>'estimatedCostUsd')::numeric, 0),
    coalesce((p_usage->>'estimatedCostUsd')::numeric, 0),
    coalesce((p_usage->>'safeBudgetUsd')::numeric, 1.25)
  )
  on conflict (session_id) do update set
    input_tokens = excluded.input_tokens,
    output_tokens = excluded.output_tokens,
    estimated_llm_cost_usd = excluded.estimated_llm_cost_usd,
    estimated_total_cost_usd = excluded.estimated_total_cost_usd,
    updated_at = now();

  insert into public.reports (
    session_id,
    learner_id,
    company_id,
    module_id,
    overall_score,
    skill_summary,
    strengths,
    improvement_areas,
    action_plan,
    generated_by,
    generated_at,
    metadata
  ) values (
    p_session_id,
    session_row.learner_id,
    session_row.company_id,
    session_row.module_id,
    (p_report->>'overallScore')::integer,
    coalesce(p_report->'skillSummary', '[]'::jsonb),
    coalesce(p_report->'strengths', '[]'::jsonb),
    coalesce(p_report->'improvementAreas', '[]'::jsonb),
    coalesce(p_report->'actionPlan', '[]'::jsonb),
    'evaluation-v2',
    now(),
    jsonb_build_object(
      'contractVersion', p_contract_version,
      'evaluationId', evaluation_row.id
    )
  )
  on conflict (session_id) do update set
    overall_score = excluded.overall_score,
    skill_summary = excluded.skill_summary,
    strengths = excluded.strengths,
    improvement_areas = excluded.improvement_areas,
    action_plan = excluded.action_plan,
    generated_by = excluded.generated_by,
    generated_at = excluded.generated_at,
    metadata = excluded.metadata;

  update public.training_sessions
  set status = 'completed',
      completed_at = coalesce(completed_at, now()),
      updated_at = now()
  where id = p_session_id;

  update public.session_evaluations
  set status = 'completed',
      completed_at = now(),
      result_metadata = jsonb_build_object(
        'resultCount', jsonb_array_length(p_results),
        'contractVersion', p_contract_version
      )
  where id = evaluation_row.id
  returning * into evaluation_row;

  return jsonb_build_object('status', 'completed', 'evaluationId', evaluation_row.id);
exception
  when others then
    update public.session_evaluations
    set status = 'failed',
        failure_code = sqlstate,
        attempt_count = attempt_count + case when id = evaluation_row.id then 0 else 1 end
    where id = evaluation_row.id;
    raise;
end;
$$;

revoke all on function public.finalize_session_evaluation(uuid, text, text, text, jsonb, jsonb, jsonb) from public;
grant execute on function public.finalize_session_evaluation(uuid, text, text, text, jsonb, jsonb, jsonb) to authenticated;

alter table public.session_evaluations enable row level security;

grant select on public.session_evaluations to authenticated;

create policy learner_read_own_evaluations on public.session_evaluations
  for select using (public.is_learner_user_for(learner_id));
create policy company_read_own_evaluations on public.session_evaluations
  for select using (public.is_company_user_for(company_id));
create policy platform_read_evaluations on public.session_evaluations
  for select using (public.is_platform_user());
