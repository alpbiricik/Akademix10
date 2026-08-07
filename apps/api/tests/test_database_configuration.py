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
            self.assertIsNone(database.get_supabase_privileged_client())

    def test_supabase_mode_requires_server_credentials(self):
        with patch.dict(os.environ, {"DATABASE_MODE": "supabase"}, clear=True):
            with self.assertRaises(database.DatabaseConfigurationError) as context:
                database.validate_database_configuration()
            self.assertIn("SUPABASE_URL", str(context.exception))
            self.assertIn("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY", str(context.exception))

    def test_supabase_mode_accepts_current_secret_key_name(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_MODE": "supabase",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SECRET_KEY": "secret-key",
            },
            clear=True,
        ):
            settings = database.validate_database_configuration()
            self.assertEqual(settings.supabase_privileged_key, "secret-key")

    def test_conflicting_privileged_keys_are_rejected(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_MODE": "supabase",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SECRET_KEY": "secret-key",
                "SUPABASE_SERVICE_ROLE_KEY": "legacy-service-role-key",
            },
            clear=True,
        ):
            with self.assertRaises(database.DatabaseConfigurationError):
                database.get_database_settings()

    def test_matching_current_and_legacy_privileged_keys_are_accepted(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_MODE": "supabase",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SECRET_KEY": "same-secret-key",
                "SUPABASE_SERVICE_ROLE_KEY": "same-secret-key",
            },
            clear=True,
        ):
            settings = database.get_database_settings()
            self.assertEqual(settings.supabase_privileged_key, "same-secret-key")

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

    def test_ambiguous_supabase_client_factory_is_guarded(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_MODE": "supabase",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret-service-role-key",
            },
            clear=True,
        ):
            with self.assertRaises(database.DatabaseConfigurationError) as context:
                database.get_supabase_client()
            self.assertIn("get_supabase_user_scoped_client", str(context.exception))


if __name__ == "__main__":
    unittest.main()
