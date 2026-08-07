-- Restrict the Phase 2B-E finalize RPC to signed-in users only.

revoke all on function public.finalize_session_evaluation(uuid, text, text, text, jsonb, jsonb, jsonb) from anon;
revoke all on function public.finalize_session_evaluation(uuid, text, text, text, jsonb, jsonb, jsonb) from public;
grant execute on function public.finalize_session_evaluation(uuid, text, text, text, jsonb, jsonb, jsonb) to authenticated;
