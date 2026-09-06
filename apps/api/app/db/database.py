import os
from dataclasses import dataclass
from enum import StrEnum

from app.core import config as _app_config  # Ensure .env is loaded



class DatabaseMode(StrEnum):
    SUPABASE = "supabase"


class DatabaseConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatabaseSettings:
    mode: DatabaseMode
    supabase_url: str | None
    supabase_privileged_key: str | None
    supabase_public_key: str | None


def _read_database_mode() -> DatabaseMode:
    raw_mode = os.getenv("DATABASE_MODE", DatabaseMode.SUPABASE.value).strip().lower()
    if raw_mode and raw_mode != DatabaseMode.SUPABASE.value:
        raise DatabaseConfigurationError("DATABASE_MODE must be supabase. Local in-memory runtime mode has been removed.")
    return DatabaseMode.SUPABASE


def get_database_settings() -> DatabaseSettings:
    secret_key = (os.getenv("SUPABASE_SECRET_KEY") or "").strip() or None
    legacy_service_role_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip() or None
    public_key = (os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip() or None
    return DatabaseSettings(
        mode=_read_database_mode(),
        supabase_url=(os.getenv("SUPABASE_URL") or "").strip() or None,
        supabase_privileged_key=secret_key or legacy_service_role_key,
        supabase_public_key=public_key,
    )



def validate_database_configuration(settings: DatabaseSettings | None = None) -> DatabaseSettings:
    active_settings = settings or get_database_settings()
    missing = []
    if not active_settings.supabase_url:
        missing.append("SUPABASE_URL")
    if not active_settings.supabase_privileged_key and not active_settings.supabase_public_key:
        missing.append("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise DatabaseConfigurationError(f"Supabase runtime requires: {', '.join(missing)}.")
    return active_settings




def get_database_mode() -> DatabaseMode:
    return get_database_settings().mode


def get_database_config_status() -> dict[str, object]:
    try:
        settings = validate_database_configuration()
        return {
            "status": "ok",
            "databaseMode": settings.mode.value,
            "supabaseConfigured": settings.mode == DatabaseMode.SUPABASE,
        }
    except DatabaseConfigurationError as error:
        mode = os.getenv("DATABASE_MODE", DatabaseMode.SUPABASE.value)
        return {
            "status": "configuration_error",
        "databaseMode": mode,
            "supabaseConfigured": False,
            "message": str(error),
        }


def get_supabase_privileged_client():
    """Create the explicit privileged Supabase client.

    This client may bypass RLS and is reserved for provisioning, migrations,
    controlled background jobs, and other internal operations. Normal
    user-scoped request handlers must not use this factory.
    """
    settings = validate_database_configuration()
    try:
        from supabase import create_client  # type: ignore[import-not-found]
    except ImportError as error:
        raise DatabaseConfigurationError("Supabase client package is not installed.") from error
    return create_client(settings.supabase_url, settings.supabase_privileged_key)


def get_supabase_user_scoped_client(access_token: str):
    """Create a future user-scoped Supabase client that preserves RLS.

    Repository integration is intentionally deferred, but this named boundary
    keeps signed-in user operations separate from the privileged server key.
    """
    settings = validate_database_configuration()
    if not settings.supabase_public_key:
        raise DatabaseConfigurationError("User-scoped Supabase client requires SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY.")
    if not access_token:
        raise DatabaseConfigurationError("User-scoped Supabase client requires a signed-in user access token.")

    try:
        from supabase import create_client  # type: ignore[import-not-found]
    except ImportError as error:
        raise DatabaseConfigurationError("Supabase client package is not installed.") from error

    client = create_client(settings.supabase_url, settings.supabase_public_key)
    client.postgrest.auth(access_token)
    return client


def get_supabase_client():
    """Deprecated ambiguous factory kept as a guard during migration."""
    raise DatabaseConfigurationError(
        "Use get_supabase_user_scoped_client() for user requests or get_supabase_privileged_client() for internal operations."
    )
