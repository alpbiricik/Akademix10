from app.services import mock_store


class CompaniesRepository:
    """Company persistence boundary backed by mock_store for now."""

    def get_company_by_id(self, company_id: str):
        return next((company for company in mock_store.companies if company.id == company_id), None)

    def list_companies(self):
        return mock_store.companies
