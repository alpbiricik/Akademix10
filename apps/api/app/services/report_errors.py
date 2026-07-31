class ReportGenerationError(Exception):
    code = "report_generation_error"


class InvalidReportInputError(ReportGenerationError):
    code = "invalid_report_input"
