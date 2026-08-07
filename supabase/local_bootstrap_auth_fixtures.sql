-- Local/disposable Supabase Auth fixtures for Phase 2B bootstrap validation.
-- Do not run against hosted development or production projects.

begin;

insert into auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at,
  confirmation_token,
  recovery_token,
  email_change_token_new,
  email_change,
  phone_change,
  phone_change_token,
  reauthentication_token,
  is_sso_user,
  is_anonymous
)
select
  '00000000-0000-0000-0000-000000000000'::uuid,
  v.id,
  'authenticated',
  'authenticated',
  v.email,
  crypt('Akademx10Local!2026', gen_salt('bf')),
  now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{}'::jsonb,
  now(),
  now(),
  '',
  '',
  '',
  '',
  '',
  '',
  '',
  false,
  false
from (values
  ('00000000-0000-0000-0000-000000000201'::uuid, 'platform@akademx10.local'),
  ('00000000-0000-0000-0000-000000000202'::uuid, 'hr@northwind.local'),
  ('00000000-0000-0000-0000-000000000203'::uuid, 'learner@northwind.local'),
  ('00000000-0000-0000-0000-000000000204'::uuid, 'learner@contoso.local'),
  ('00000000-0000-0000-0000-000000000205'::uuid, 'hr@contoso.local')
) as v(id, email)
on conflict (id) do update set
  email = excluded.email,
  encrypted_password = excluded.encrypted_password,
  email_confirmed_at = excluded.email_confirmed_at,
  raw_app_meta_data = excluded.raw_app_meta_data,
  updated_at = excluded.updated_at;

insert into auth.identities (
  id,
  provider_id,
  user_id,
  identity_data,
  provider,
  last_sign_in_at,
  created_at,
  updated_at
)
select
  v.id::text,
  v.id::text,
  v.id,
  jsonb_build_object('sub', v.id::text, 'email', v.email),
  'email',
  now(),
  now(),
  now()
from (values
  ('00000000-0000-0000-0000-000000000201'::uuid, 'platform@akademx10.local'),
  ('00000000-0000-0000-0000-000000000202'::uuid, 'hr@northwind.local'),
  ('00000000-0000-0000-0000-000000000203'::uuid, 'learner@northwind.local'),
  ('00000000-0000-0000-0000-000000000204'::uuid, 'learner@contoso.local'),
  ('00000000-0000-0000-0000-000000000205'::uuid, 'hr@contoso.local')
) as v(id, email)
on conflict (provider_id, provider) do update set
  user_id = excluded.user_id,
  identity_data = excluded.identity_data,
  updated_at = excluded.updated_at;

commit;
