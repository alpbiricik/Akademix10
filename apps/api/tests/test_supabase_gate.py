import unittest
from pathlib import Path

from app.routers import health


ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "supabase" / "migrations"


class SupabaseGateTests(unittest.TestCase):
    def test_expected_migration_order_exists(self):
        self.assertTrue((MIGRATIONS / "0001_initial_schema.sql").exists())
        self.assertTrue((MIGRATIONS / "0002_rls_policies.sql").exists())
        self.assertTrue((MIGRATIONS / "0003_seed_demo_data.sql").exists())
        self.assertTrue((MIGRATIONS / "0009_restrict_finalize_rpc_grants.sql").exists())
        self.assertTrue((MIGRATIONS / "0007_restrict_session_evaluation_table_grants.sql").exists())
        self.assertTrue((MIGRATIONS.parent / "local_bootstrap_auth_fixtures.sql").exists())
        self.assertTrue((MIGRATIONS.parent / "bootstrap-local-development.ps1").exists())

    def test_schema_limits_active_app_roles(self):
        schema = (MIGRATIONS / "0001_initial_schema.sql").read_text(encoding="utf-8")
        self.assertIn("role in ('platform', 'company', 'learner')", schema)
        self.assertNotIn("'admin'", schema)
        self.assertNotIn("'trainer'", schema)
        self.assertNotIn("'company_admin'", schema)

    def test_schema_maps_public_users_to_auth_users(self):
        schema = (MIGRATIONS / "0001_initial_schema.sql").read_text(encoding="utf-8")
        self.assertIn("id uuid primary key references auth.users(id) on delete cascade", schema)
        self.assertNotIn("auth_user_id", schema)

    def test_company_membership_is_canonical_tenant_source(self):
        schema = (MIGRATIONS / "0001_initial_schema.sql").read_text(encoding="utf-8")
        users_table = schema.split("create table public.company_members", 1)[0]
        self.assertNotIn("company_id uuid", users_table)
        self.assertIn("idx_company_members_one_active_user", schema)
        self.assertIn("enforce_company_membership_consistency", schema)
        self.assertIn("if tg_table_name = 'users' then", schema)
        self.assertIn("target_user_id = old.user_id", schema)
        self.assertIn("Platform users must not have company membership.", schema)
        self.assertIn("Company and learner users require exactly one active company membership.", schema)

    def test_schema_hardens_tenant_ownership_paths(self):
        schema = (MIGRATIONS / "0001_initial_schema.sql").read_text(encoding="utf-8")
        self.assertIn("enforce_enrollment_consistency", schema)
        self.assertIn("enforce_session_consistency", schema)
        self.assertIn("enforce_answer_consistency", schema)
        self.assertIn("unique(session_id, state_id, answer_id)", schema)
        self.assertIn("unique(session_id, state_id, skill, source)", schema)

    def test_rls_file_has_real_policies_and_helpers(self):
        rls = (MIGRATIONS / "0002_rls_policies.sql").read_text(encoding="utf-8").lower()
        self.assertIn("auth.uid()", rls)
        self.assertIn("create function public.current_app_role()", rls)
        self.assertIn("security definer", rls)
        self.assertIn("set search_path = public, pg_temp", rls)
        self.assertIn("create policy", rls)
        self.assertNotIn("todo", rls)
        self.assertNotIn("not production-final", rls)

    def test_rls_rejects_client_spoofing_sources(self):
        rls = (MIGRATIONS / "0002_rls_policies.sql").read_text(encoding="utf-8").lower()
        self.assertNotIn("raw_user_meta_data", rls)
        self.assertNotIn("x-mock-role", rls)
        self.assertNotIn("localstorage", rls)
        self.assertIn("public.current_app_role()", rls)
        self.assertIn("public.current_app_company_id()", rls)

    def test_rls_scope_for_platform_company_learner_and_anon(self):
        rls = (MIGRATIONS / "0002_rls_policies.sql").read_text(encoding="utf-8").lower()
        self.assertIn("revoke all on all tables in schema public from anon", rls)
        self.assertIn("platform_all_companies", rls)
        self.assertIn("company_read_own_sessions", rls)
        self.assertIn("learner_read_own_sessions", rls)
        self.assertIn("learner_insert_own_answers", rls)
        self.assertNotIn("grant all", rls)

    def test_seed_is_idempotent_and_does_not_write_auth_users(self):
        seed = (MIGRATIONS / "0003_seed_demo_data.sql").read_text(encoding="utf-8").lower()
        self.assertIn("on conflict", seed)
        self.assertIn("where exists (select 1 from auth.users", seed)
        self.assertNotIn("insert into auth.users", seed)
        self.assertNotIn("delete from", seed)
        self.assertNotIn("truncate", seed)
        self.assertIn("00000000-0000-0000-0000-000000000102", seed)
        self.assertIn("00000000-0000-0000-0000-000000000204", seed)
        self.assertIn("00000000-0000-0000-0000-000000000205", seed)
        self.assertIn("00000000-0000-0000-0000-000000000902", seed)

    def test_health_config_shape_is_secret_free(self):
        payload = health.health_config()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("database", payload)
        rendered = str(payload).lower()
        self.assertNotIn("service_role_key", rendered)
        self.assertNotIn("anon_key", rendered)

    def test_finalize_rpc_is_not_executable_by_anon(self):
        migration = (MIGRATIONS / "0009_restrict_finalize_rpc_grants.sql").read_text(encoding="utf-8").lower()
        self.assertIn("revoke all on function public.finalize_session_evaluation", migration)
        self.assertIn("from anon", migration)
        self.assertIn("grant execute on function public.finalize_session_evaluation", migration)
        self.assertIn("to authenticated", migration)

    def test_session_evaluations_table_is_not_accessible_to_anon(self):
        migration = (MIGRATIONS / "0007_restrict_session_evaluation_table_grants.sql").read_text(encoding="utf-8").lower()
        self.assertIn("revoke all on table public.session_evaluations from anon", migration)
        self.assertIn("revoke all on table public.session_evaluations from public", migration)
        self.assertIn("revoke all on table public.session_evaluations from authenticated", migration)
        self.assertIn("grant select on table public.session_evaluations to authenticated", migration)

    def test_local_bootstrap_script_is_local_only_and_idempotency_aware(self):
        script = (MIGRATIONS.parent / "bootstrap-local-development.ps1").read_text(encoding="utf-8").lower()
        self.assertIn("--local", script)
        self.assertIn("0003_seed_demo_data.sql", script)
        self.assertIn("iunderstandthisisdisposable", script)
        self.assertNotIn("--linked", script)
        self.assertNotIn(" db reset", script)
        self.assertNotIn("truncate", script)
        self.assertEqual(script.count("0003_seed_demo_data.sql"), 2)


if __name__ == "__main__":
    unittest.main()
