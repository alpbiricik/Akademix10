from fastapi import APIRouter, Depends

from app.db.database import DatabaseMode, get_database_mode
from app.db.supabase_rest import SupabaseUserClient

from app.core.auth import Principal, get_current_principal

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
def get_me(principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    name = ""
    title = ""
    if get_database_mode() == DatabaseMode.SUPABASE and principal.access_token:
        rows = SupabaseUserClient(principal.access_token).select("users", f"select=full_name,title&id=eq.{principal.user_id}&limit=1")
        if rows:
            name = rows[0].get("full_name") or ""
            title = rows[0].get("title") or ""
    return {
        "id": principal.user_id,
        "name": name,
        "role": principal.role,
        "title": title,
        "companyId": principal.company_id,
    }
