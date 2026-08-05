import os
import unittest
from unittest.mock import patch

from app.db import database


class DatabaseConfigurationTests(unittest.TestCase):
    def test_mock_mode_does_not_require_supabase_credentials(self):
        with patch.dict(os.environ, {"DATABASE_MODE": "mock"}, clear=True):
            settings = database.validate_database_configuration()
            self.assertEqual(settings.mode, database.DatabaseMode.MOCK)
            self.assertIsNone(database.get_supabase_client())

    def test_supabase_mode_requires_server_credentials(self):
        with patch.dict(os.environ, {"DATABASE_MODE": "supabase"}, clear=True):
            with self.assertRaises(database.DatabaseConfigurationError) as context:
                database.validate_database_configuration()
            self.assertIn("SUPABASE_URL", str(context.exception))
            self.assertIn("SUPABASE_SERVICE_ROLE_KEY", str(context.exception))

    def test_invalid_database_mode_is_rejected(self):
        with patch.dict(os.environ, {"DATABASE_MODE": "production"}, clear=True):
            with self.assertRaises(database.DatabaseConfigurationError):
                database.get_database_settings()

    def test_health_config_status_is_secret_free(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_MODE": "supabase",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret-service-role-key",
            },
            clear=True,
        ):
            status = database.get_database_config_status()
            rendered = str(status)
            self.assertEqual(status["status"], "ok")
            self.assertNotIn("secret-service-role-key", rendered)
            self.assertNotIn("https://example.supabase.co", rendered)


if __name__ == "__main__":
    unittest.main()
