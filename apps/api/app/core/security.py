from collections.abc import Callable
from typing import Literal

from fastapi import Header, HTTPException, status

Role = Literal["platform", "company", "learner"]
ALLOWED_ROLES: set[str] = {"platform", "company", "learner"}


def get_mock_role_from_header(x_mock_role: str | None = Header(default=None)) -> Role:
    if not x_mock_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-mock-role header.",
        )
    if x_mock_role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid mock role.",
        )
    return x_mock_role  # type: ignore[return-value]


def require_role(*roles: Role) -> Callable[[str | None], Role]:
    def dependency(x_mock_role: str | None = Header(default=None, alias="x-mock-role")) -> Role:
        if not x_mock_role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing x-mock-role header.")
        if x_mock_role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid mock role.")
        if x_mock_role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not allowed for this route.")
        return x_mock_role  # type: ignore[return-value]

    return dependency
