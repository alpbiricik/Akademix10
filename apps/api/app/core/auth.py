from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Header, HTTPException, status

from app.core.security import MOCK_PRINCIPALS, MockPrincipal, Role
from app.db.database import DatabaseMode, get_database_mode
from app.db.supabase_rest import SupabaseRequestError, SupabaseUserClient, verify_access_token


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    company_id: str | None = None
    access_token: str | None = None


def _mock_principal(x_mock_role: str | None) -> Principal:
    if not x_mock_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing x-mock-role header.")
    if x_mock_role not in MOCK_PRINCIPALS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid mock role.")
    principal = MOCK_PRINCIPALS[x_mock_role]
    return Principal(user_id=principal.user_id, role=principal.role, company_id=principal.company_id)


def get_current_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_mock_role: str | None = Header(default=None, alias="x-mock-role"),
) -> Principal:
    if get_database_mode() == DatabaseMode.MOCK:
        return _mock_principal(x_mock_role)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        user = verify_access_token(token)
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")
        client = SupabaseUserClient(token)
        profiles = client.select("users", f"select=id,full_name,role,title,status&id=eq.{user_id}&limit=1")
        if not profiles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trusted profile not found.")
        profile = profiles[0]
        role = profile.get("role")
        if role not in {"platform", "company", "learner"} or profile.get("status") != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile is not active.")
        company_id = None
        if role in {"company", "learner"}:
            memberships = client.select("company_members", f"select=company_id&user_id=eq.{user_id}&status=eq.active&limit=1")
            if not memberships:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active company membership not found.")
            company_id = memberships[0]["company_id"]
        return Principal(user_id=user_id, role=role, company_id=company_id, access_token=token)  # type: ignore[arg-type]
    except SupabaseRequestError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED if error.status_code in {401, 403} else status.HTTP_502_BAD_GATEWAY, detail="Authentication failed.") from error


def require_role(*roles: Literal["platform", "company", "learner"]):
    def dependency(
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_mock_role: str | None = Header(default=None, alias="x-mock-role"),
    ) -> Principal:
        principal = get_current_principal(authorization=authorization, x_mock_role=x_mock_role)
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not allowed for this route.")
        return principal

    return dependency


def to_mock_principal(principal: Principal) -> MockPrincipal:
    return MockPrincipal(user_id=principal.user_id, role=principal.role, company_id=principal.company_id)
