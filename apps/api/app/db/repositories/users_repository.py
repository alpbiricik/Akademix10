from app.services import mock_store


class UsersRepository:
    """User persistence boundary.

    Uses mock_store for Phase 2G. TODO: replace internals with Supabase queries.
    """

    def get_user_by_id(self, user_id: str):
        return next((user for user in mock_store.users if user.id == user_id), None)

    def get_user_by_email(self, email: str):
        # Mock DTOs do not carry email yet.
        _ = email
        return None

    def get_users_by_company(self, company_id: str):
        return [user for user in mock_store.users if user.companyId == company_id]
