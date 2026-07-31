from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import MockPrincipal, get_mock_principal, require_role
from app.schemas.dtos import CompanyAggregateReportDTO, ReportDTO, TrainingTemplateDTO, UserDTO
from app.services import mock_store
from app.services import report_endpoint_service
from app.services.report_errors import ReportGenerationError

router = APIRouter(prefix="/api/company", tags=["company"], dependencies=[Depends(require_role("company"))])


def raise_report_http_error(error: ReportGenerationError) -> None:
    raise HTTPException(
        status_code=report_endpoint_service.to_http_status(error),
        detail={"code": error.code, "message": str(error)},
    )


@router.get("/trainings", response_model=list[TrainingTemplateDTO])
def get_company_trainings() -> list[TrainingTemplateDTO]:
    return mock_store.get_company_templates("company-demo")


@router.get("/employees", response_model=list[UserDTO])
def get_company_employees() -> list[UserDTO]:
    return [user for user in mock_store.users if user.companyId == "company-demo"]


@router.get("/reports/aggregate", response_model=CompanyAggregateReportDTO)
def get_company_aggregate_report(
    template_id: str | None = Query(default=None, alias="templateId"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    principal: MockPrincipal = Depends(get_mock_principal),
) -> CompanyAggregateReportDTO:
    try:
        return report_endpoint_service.get_company_aggregate_report(principal, template_id=template_id, date_from=date_from, date_to=date_to)
    except ReportGenerationError as error:
        raise_report_http_error(error)


@router.get("/reports", response_model=list[ReportDTO])
def get_company_reports() -> list[ReportDTO]:
    return [mock_store.demo_report]


@router.get("/usage")
def get_company_usage() -> dict[str, object]:
    return {"scope": "company", "companyId": "company-demo", "sessionUsage": mock_store.demo_session.usage.model_dump()}
