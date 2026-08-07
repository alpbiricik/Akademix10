-- Fix membership consistency trigger for both public.users and public.company_members.

create or replace function public.enforce_company_membership_consistency() returns trigger
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
