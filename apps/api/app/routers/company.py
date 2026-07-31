from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.schemas.dtos import ReportDTO, TrainingTemplateDTO, UserDTO
from app.services import mock_store

router = APIRouter(prefix="/api/company", tags=["company"], dependencies=[Depends(require_role("company"))])


@router.get("/trainings", response_model=list[TrainingTemplateDTO])
def get_company_trainings() -> list[TrainingTemplateDTO]:
    return mock_store.get_company_templates("company-demo")


@router.get("/employees", response_model=list[UserDTO])
def get_company_employees() -> list[UserDTO]:
    return [user for user in mock_store.users if user.companyId == "company-demo"]


@router.get("/reports", response_model=list[ReportDTO])
def get_company_reports() -> list[ReportDTO]:
    return [mock_store.demo_report]


@router.get("/usage")
def get_company_usage() -> dict[str, object]:
    return {"scope": "company", "companyId": "company-demo", "sessionUsage": mock_store.demo_session.usage.model_dump()}
