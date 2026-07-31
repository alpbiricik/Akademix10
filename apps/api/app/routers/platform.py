from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.schemas.dtos import CompanyDTO, TrainingTemplateDTO
from app.services import mock_store

router = APIRouter(prefix="/api/platform", tags=["platform"], dependencies=[Depends(require_role("platform"))])


@router.get("/templates", response_model=list[TrainingTemplateDTO])
def get_templates() -> list[TrainingTemplateDTO]:
    return mock_store.training_templates


@router.post("/templates", response_model=TrainingTemplateDTO)
def create_template() -> TrainingTemplateDTO:
    template = mock_store.training_templates[0].model_copy(deep=True)
    template.id = f"template-mock-created-{int(datetime.now(timezone.utc).timestamp())}"
    template.title = "Mock Created Template"
    template.status = "draft"
    return template


@router.get("/companies", response_model=list[CompanyDTO])
def get_companies() -> list[CompanyDTO]:
    return mock_store.companies


@router.post("/companies", response_model=CompanyDTO)
def create_company() -> CompanyDTO:
    return CompanyDTO(
        id=f"company-mock-{int(datetime.now(timezone.utc).timestamp())}",
        name="Mock Created Company",
        industry="Mock Industry",
        learnerCount=0,
        assignedTrainingTemplateIds=[],
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/assignments")
def create_assignment() -> dict[str, object]:
    return {"status": "mock_assigned", "enrollments": [item.model_dump() for item in mock_store.enrollments]}


@router.get("/assignments")
def get_assignments() -> list[dict[str, object]]:
    return [
        {
            "id": "assignment-demo",
            "templateId": "template-sales-communication",
            "companyId": "company-demo",
            "status": "active",
        }
    ]


@router.get("/usage")
def get_platform_usage() -> dict[str, object]:
    return {"scope": "platform", "sessionUsage": mock_store.demo_session.usage.model_dump(), "companyCount": len(mock_store.companies)}
