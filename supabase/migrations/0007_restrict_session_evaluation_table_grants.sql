-- Tighten grants for the evaluation lifecycle table.

revoke all on table public.session_evaluations from anon;
revoke all on table public.session_evaluations from public;
revoke all on table public.session_evaluations from authenticated;
grant select on table public.session_evaluations to authenticated;
