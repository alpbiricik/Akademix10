from datetime import datetime, timezone

from app.core.security import MockPrincipal
from app.db.repositories.reports_repository import ReportsRepository
from app.schemas.dtos import (
    CompanyAggregateReportDTO,
    LearnerSessionReportDTO,
    PlatformAggregateReportDTO,
    StructuredScoringResultDTO,
    TrainingSessionDTO,
)
from app.services import mock_store, report_generation_service, scoring_repository
from app.services.report_errors import InvalidReportInputError, ReportGenerationError


class ReportAccessError(ReportGenerationError):
    code = "report_access_denied"


class ReportNotFoundError(ReportGenerationError):
    code = "report_not_found"


class InvalidReportFilterError(ReportGenerationError):
    code = "invalid_report_filter"


def parse_iso_datetime(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as error:
        raise InvalidReportFilterError(f"{field_name} must be ISO-8601.") from error


def validate_report_filters(template_id: str | None = None, date_from: str | None = None, date_to: str | None = None) -> dict[str, object]:
    parsed_from = parse_iso_datetime(date_from, "dateFrom")
    parsed_to = parse_iso_datetime(date_to, "dateTo")
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise InvalidReportFilterError("dateFrom must be before or equal to dateTo.")
    if template_id and not any(template.id == template_id for template in mock_store.training_templates):
        raise InvalidReportFilterError("Unknown templateId.")
    return {
        "templateId": template_id,
        "dateFrom": date_from,
        "dateTo": date_to,
    }


def filter_sessions(
    sessions: list[TrainingSessionDTO],
    template_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[TrainingSessionDTO]:
    parsed_from = parse_iso_datetime(date_from, "dateFrom")
    parsed_to = parse_iso_datetime(date_to, "dateTo")
    filtered = sessions
    if template_id:
        filtered = [session for session in filtered if session.templateId == template_id]
    if parsed_from:
        filtered = [session for session in filtered if parse_iso_datetime(session.startedAt, "startedAt") and parse_iso_datetime(session.startedAt, "startedAt") >= parsed_from]
    if parsed_to:
        filtered = [session for session in filtered if parse_iso_datetime(session.startedAt, "startedAt") and parse_iso_datetime(session.startedAt, "startedAt") <= parsed_to]
    return sorted(filtered, key=lambda session: session.id)


def get_session_for_learner(session_id: str, principal: MockPrincipal) -> TrainingSessionDTO:
    session = mock_store.sessions.get(session_id)
    if not session or session.userId != principal.user_id:
        raise ReportNotFoundError("Session not found.")
    return session


def get_template(template_id: str):
    return next((template for template in mock_store.training_templates if template.id == template_id), mock_store.training_templates[0])


def get_module(module_id: str):
    return next((module for module in mock_store.training_modules if module.id == module_id), mock_store.training_modules[0])


def get_learner_scoring_results(session_id: str, principal: MockPrincipal) -> list[StructuredScoringResultDTO]:
    get_session_for_learner(session_id, principal)
    results = [result for result in scoring_repository.list_scoring_results() if result.sessionId == session_id]
    return report_generation_service.dedupe_latest_scoring_results(results)


def get_learner_session_report(session_id: str, principal: MockPrincipal) -> LearnerSessionReportDTO:
    session = get_session_for_learner(session_id, principal)
    report = report_generation_service.generate_learner_session_report(
        session=session,
        states=mock_store.training_states,
        scoring_results=scoring_repository.list_scoring_results(),
        template=get_template(session.templateId),
        module=get_module(session.moduleId),
    )
    ReportsRepository().create_report(report)
    return report


def get_company_aggregate_report(
    principal: MockPrincipal,
    template_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> CompanyAggregateReportDTO:
    if not principal.company_id:
        raise ReportAccessError("Company context is required.")
    filter_summary = validate_report_filters(template_id, date_from, date_to)
    company = next((item for item in mock_store.companies if item.id == principal.company_id), None)
    if not company:
        raise ReportNotFoundError("Company report not found.")
    sessions = filter_sessions(list(mock_store.sessions.values()), template_id=template_id, date_from=date_from, date_to=date_to)
    report = report_generation_service.generate_company_aggregate_report(
        company=company,
        sessions=sessions,
        scoring_results=scoring_repository.list_scoring_results(),
        template=get_template(template_id) if template_id else None,
        filter_summary=filter_summary,
    )
    ReportsRepository().create_report(report)
    return report


def get_platform_aggregate_report(
    template_id: str | None = None,
    company_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> PlatformAggregateReportDTO:
    filter_summary = validate_report_filters(template_id, date_from, date_to)
    if company_id and not any(company.id == company_id for company in mock_store.companies):
        raise InvalidReportFilterError("Unknown companyId.")
    sessions = filter_sessions(list(mock_store.sessions.values()), template_id=template_id, date_from=date_from, date_to=date_to)
    if company_id:
        sessions = [session for session in sessions if session.companyId == company_id]
        filter_summary["companyId"] = company_id
    report = report_generation_service.generate_platform_aggregate_report(
        companies=mock_store.companies,
        templates=mock_store.training_templates,
        sessions=sessions,
        scoring_results=scoring_repository.list_scoring_results(),
    )
    ReportsRepository().create_report(report)
    return report


def to_http_status(error: ReportGenerationError) -> int:
    if isinstance(error, InvalidReportFilterError) or isinstance(error, InvalidReportInputError):
        return 422
    if isinstance(error, ReportAccessError):
        return 403
    if isinstance(error, ReportNotFoundError):
        return 404
    return 500
