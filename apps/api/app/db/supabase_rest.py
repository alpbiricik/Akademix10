import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.db.database import (
    DatabaseConfigurationError,
    get_database_settings,
    validate_database_configuration,
)



class SupabaseRequestError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _public_key() -> str:
    settings = get_database_settings()
    key = settings.supabase_public_key or settings.supabase_privileged_key
    if not key:
        raise DatabaseConfigurationError("Supabase user-scoped requests require SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY.")
    return key


def _base_url() -> str:
    settings = get_database_settings()
    if not settings.supabase_url:
        raise DatabaseConfigurationError("Supabase URL is required.")
    return settings.supabase_url.rstrip("/")



def _request(method: str, url: str, headers: dict[str, str], payload: Any | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        message = "Supabase request failed."
        if body:
            try:
                parsed = json.loads(body)
                message = parsed.get("message") or parsed.get("msg") or message
            except json.JSONDecodeError:
                message = "Supabase request failed."
        raise SupabaseRequestError(error.code, message) from error


def verify_access_token(access_token: str) -> dict[str, Any]:
    headers = {
        "apikey": _public_key(),
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    return _request("GET", f"{_base_url()}/auth/v1/user", headers)


class SupabaseUserClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base = f"{_base_url()}/rest/v1"
        self.headers = {
            "apikey": _public_key(),
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def select(self, table: str, query: str = "select=*") -> list[dict[str, Any]]:
        payload = _request("GET", f"{self.base}/{table}?{query}", self.headers)
        return payload if isinstance(payload, list) else []

    def insert(self, table: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {**self.headers, "Prefer": "return=representation"}
        result = _request("POST", f"{self.base}/{table}", headers, payload)
        return result if isinstance(result, list) else []

    def patch(self, table: str, query: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {**self.headers, "Prefer": "return=representation"}
        result = _request("PATCH", f"{self.base}/{table}?{query}", headers, payload)
        return result if isinstance(result, list) else []

    def rpc(self, function_name: str, payload: dict[str, Any]) -> Any:
        headers = {**self.headers, "Prefer": "return=representation"}
        return _request("POST", f"{self.base}/rpc/{function_name}", headers, payload)


def query_param(value: str) -> str:
    return urllib.parse.quote(value, safe="")
