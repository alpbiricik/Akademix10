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
    supabase_service_role_key: str | None


def _read_database_mode() -> DatabaseMode:
    raw_mode = os.getenv("DATABASE_MODE", DatabaseMode.MOCK.value).strip().lower()
    try:
        return DatabaseMode(raw_mode)
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in DatabaseMode)
        raise DatabaseConfigurationError(f"Invalid DATABASE_MODE. Expected one of: {allowed}.") from error


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        mode=_read_database_mode(),
        supabase_url=os.getenv("SUPABASE_URL") or None,
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
    )


def validate_database_configuration(settings: DatabaseSettings | None = None) -> DatabaseSettings:
    active_settings = settings or get_database_settings()
    if active_settings.mode == DatabaseMode.SUPABASE:
        missing = []
        if not active_settings.supabase_url:
            missing.append("SUPABASE_URL")
        if not active_settings.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
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


def get_supabase_client():
    """Central future Supabase client factory.

    Phase 2B-A validates configuration and keeps client creation centralized.
    Repository integration is intentionally deferred.
    """
    settings = validate_database_configuration()
    if settings.mode == DatabaseMode.MOCK:
        return None

    try:
        from supabase import create_client  # type: ignore[import-not-found]
    except ImportError as error:
        raise DatabaseConfigurationError("Supabase client package is not installed.") from error
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
