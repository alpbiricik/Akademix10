import os
from dataclasses import dataclass
from enum import StrEnum


class DatabaseMode(StrEnum):
    MOCK = "mock"
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
    raw_mode = os.getenv("DATABASE_MODE", DatabaseMode.MOCK.value).strip().lower()
    try:
        return DatabaseMode(raw_mode)
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in DatabaseMode)
        raise DatabaseConfigurationError(f"Invalid DATABASE_MODE. Expected one of: {allowed}.") from error


def get_database_settings() -> DatabaseSettings:
    secret_key = os.getenv("SUPABASE_SECRET_KEY") or None
    legacy_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None
    public_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or None
    if secret_key and legacy_service_role_key and secret_key != legacy_service_role_key:
        raise DatabaseConfigurationError(
            "Define only one backend privileged Supabase key: SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY."
        )
    return DatabaseSettings(
        mode=_read_database_mode(),
        supabase_url=os.getenv("SUPABASE_URL") or None,
        supabase_privileged_key=secret_key or legacy_service_role_key,
        supabase_public_key=public_key,
    )


def validate_database_configuration(settings: DatabaseSettings | None = None) -> DatabaseSettings:
    active_settings = settings or get_database_settings()
    if active_settings.mode == DatabaseMode.SUPABASE:
        missing = []
        if not active_settings.supabase_url:
            missing.append("SUPABASE_URL")
        if not active_settings.supabase_privileged_key:
            missing.append("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY")
        if missing:
            raise DatabaseConfigurationError(f"Supabase mode requires: {', '.join(missing)}.")
    return active_settings


def is_mock_database() -> bool:
    return get_database_settings().mode == DatabaseMode.MOCK


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
        mode = os.getenv("DATABASE_MODE", DatabaseMode.MOCK.value)
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
    if settings.mode == DatabaseMode.MOCK:
        return None

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
    if settings.mode == DatabaseMode.MOCK:
        return None
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
    if get_database_settings().mode == DatabaseMode.MOCK:
        return None
    raise DatabaseConfigurationError(
        "Use get_supabase_user_scoped_client() for user requests or get_supabase_privileged_client() for internal operations."
    )
