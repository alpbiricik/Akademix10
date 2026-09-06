from typing import Literal

Role = Literal["platform", "company", "learner"]
ALLOWED_ROLES: set[str] = {"platform", "company", "learner"}
