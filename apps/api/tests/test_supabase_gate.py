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

    def test_schema_limits_active_app_roles(self):
        schema = (MIGRATIONS / "0001_initial_schema.sql").read_text(encoding="utf-8")
        self.assertIn("role in ('platform', 'company', 'learner')", schema)
        self.assertNotIn("'admin'", schema)
        self.assertNotIn("'trainer'", schema)
        self.assertNotIn("'company_admin'", schema)

    def test_rls_file_is_marked_as_draft(self):
        rls = (MIGRATIONS / "0002_rls_policies.sql").read_text(encoding="utf-8").lower()
        self.assertIn("not production-final", rls)
        self.assertIn("do not apply it as", rls)
        self.assertIn("auth.uid()", rls)

    def test_health_config_shape_is_secret_free(self):
        payload = health.health_config()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("database", payload)
        rendered = str(payload).lower()
        self.assertNotIn("service_role_key", rendered)
        self.assertNotIn("anon_key", rendered)


if __name__ == "__main__":
    unittest.main()
