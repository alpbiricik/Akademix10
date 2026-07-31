import os
from enum import StrEnum


class DatabaseMode(StrEnum):
    MOCK = "mock"
    SUPABASE = "supabase"


DATABASE_MODE = DatabaseMode(os.getenv("DATABASE_MODE", DatabaseMode.MOCK.value))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def is_mock_database() -> bool:
    return DATABASE_MODE == DatabaseMode.MOCK


def get_database_mode() -> DatabaseMode:
    return DATABASE_MODE


def get_supabase_client_placeholder():
    """Future Supabase client factory.

    Phase 2G intentionally does not import or initialize a real Supabase client.
    TODO: add the official client and credentials only after a real Supabase project,
    auth mapping, RLS testing, and secret management are ready.
    """
    if DATABASE_MODE == DatabaseMode.SUPABASE:
        raise NotImplementedError("Supabase mode is not connected in Phase 2G.")
    return None
