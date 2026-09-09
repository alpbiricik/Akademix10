-- Additive content-free observations; no changes to existing RLS or usage columns.
alter table public.session_usage add column if not exists voice_metrics_summary jsonb;
create or replace function public.persist_voice_usage_summary(p_session_id uuid, p_summary jsonb)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare
  session_row public.training_sessions%rowtype;
  item record;
begin
  if auth.uid() is null then raise exception 'Authentication required.'; end if;
  select * into session_row from public.training_sessions where id = p_session_id for update;
  if not found or session_row.learner_id <> auth.uid() then raise exception 'Session not found.'; end if;
  if not exists (
    select 1 from public.users u join public.company_members cm on cm.user_id = u.id
    where u.id = auth.uid() and u.role = 'learner' and u.status = 'active'
      and cm.company_id = session_row.company_id and cm.status = 'active'
  ) then raise exception 'Active learner membership required.'; end if;
  if not exists (
    select 1 from public.learner_enrollments le
    where le.id = session_row.enrollment_id and le.learner_id = auth.uid()
      and le.company_id = session_row.company_id
      and le.status in ('not_started', 'in_progress', 'completed')
  ) then raise exception 'Session enrollment is not active.'; end if;
  if p_summary is null or jsonb_typeof(p_summary) <> 'object' or octet_length(p_summary::text) > 16384 then
    raise exception 'Invalid metrics summary.';
  end if;
  for item in select key, value from jsonb_each(p_summary) loop
    if not (item.key = any(array['actual_avatar_billable_seconds', 'actual_cost_usd', 'actual_stt_billable_seconds', 'actual_tts_credits', 'avatar_delivery_p50_ms', 'avatar_delivery_p95_ms', 'avatar_delivery_samples', 'browser_end_to_end_p50_ms', 'browser_end_to_end_p95_ms', 'browser_end_to_end_samples', 'browser_first_frame_p50_ms', 'browser_first_frame_p95_ms', 'browser_first_frame_samples', 'browser_playback_p50_ms', 'browser_playback_p95_ms', 'browser_playback_samples', 'conversation_first_token_p50_ms', 'conversation_first_token_p95_ms', 'conversation_first_token_samples', 'conversation_response_p50_ms', 'conversation_response_p95_ms', 'conversation_response_samples', 'count_avatar_delivery', 'count_avatar_start', 'count_avatar_stop', 'count_browser_end_to_end', 'count_browser_first_frame', 'count_browser_playback', 'count_cancel', 'count_conversation', 'count_conversation_first_token', 'count_error', 'count_fallback', 'count_retry', 'count_stt', 'count_stt_partial', 'count_tts', 'dropped_observations', 'estimated_audio_seconds_cost_usd', 'estimated_avatar_seconds_cost_usd', 'estimated_input_tokens_cost_usd', 'estimated_output_tokens_cost_usd', 'estimated_total_cost_usd', 'estimated_tts_characters_cost_usd', 'observation_count', 'schema_version', 'stt_final_p50_ms', 'stt_final_p95_ms', 'stt_final_samples', 'stt_partial_p50_ms', 'stt_partial_p95_ms', 'stt_partial_samples', 'tts_first_audio_p50_ms', 'tts_first_audio_p95_ms', 'tts_first_audio_samples', 'usage_audio_seconds', 'usage_avatar_seconds', 'usage_input_tokens', 'usage_output_tokens', 'usage_tts_characters'])) then raise exception 'Unsupported metric field.'; end if;
    if jsonb_typeof(item.value) not in ('number', 'null') then raise exception 'Metrics must be numeric.'; end if;
    if jsonb_typeof(item.value) = 'number' and ((item.value::text)::numeric < 0 or (item.value::text)::numeric > 1000000000000000) then
      raise exception 'Metric out of range.';
    end if;
    if item.key like 'actual_%' and item.value <> 'null'::jsonb then
      raise exception 'Provider billing requires external verification.';
    end if;
  end loop;
  if p_summary->>'schema_version' is distinct from '1' or coalesce((p_summary->>'observation_count')::numeric, 0) <= 0 then
    raise exception 'Invalid summary version or count.';
  end if;
  insert into public.session_usage(session_id, voice_metrics_summary) values (p_session_id, p_summary)
  on conflict (session_id) do update set voice_metrics_summary = excluded.voice_metrics_summary
    where coalesce((session_usage.voice_metrics_summary->>'observation_count')::numeric, 0)
      <= (excluded.voice_metrics_summary->>'observation_count')::numeric;
  return true;
end;
$$;
revoke all on function public.persist_voice_usage_summary(uuid, jsonb) from public, anon;
grant execute on function public.persist_voice_usage_summary(uuid, jsonb) to authenticated;
comment on column public.session_usage.voice_metrics_summary is 'Numeric POC observations, not authoritative provider billing. No conversation content.';
