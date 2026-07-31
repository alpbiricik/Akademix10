from app.services import mock_store

_generated_reports: dict[str, object] = {}


class ReportsRepository:
    """Report persistence boundary backed by mock_store for now."""

    def get_report_by_session(self, session_id: str):
        if session_id == mock_store.demo_report.sessionId:
            return mock_store.demo_report
        return None

    def create_report(self, report):
        _generated_reports[getattr(report, "id", f"report-{len(_generated_reports) + 1}")] = report
        return report

    def get_generated_report(self, report_id: str):
        return _generated_reports.get(report_id)

    def list_generated_reports(self):
        return [value for _, value in sorted(_generated_reports.items())]

    def clear_generated_reports(self):
        _generated_reports.clear()
