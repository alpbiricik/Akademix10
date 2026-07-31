from app.services import mock_store


class ReportsRepository:
    """Report persistence boundary backed by mock_store for now."""

    def get_report_by_session(self, session_id: str):
        if session_id == mock_store.demo_report.sessionId:
            return mock_store.demo_report
        return None

    def create_report(self, report):
        # TODO: persist generated reports in Supabase.
        return report
