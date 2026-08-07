from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import Principal, require_role
from app.db.database import DatabaseMode, get_database_mode
from app.db.supabase_mappers import company_from_row, template_from_row, usage_from_row
from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import CompanyDTO, PlatformAggregateReportDTO, TrainingTemplateDTO
from app.services import mock_store
from app.services import report_endpoint_service
from app.services.report_errors import ReportGenerationError

router = APIRouter(prefix="/api/platform", tags=["platform"])


def raise_report_http_error(error: ReportGenerationError) -> None:
    raise HTTPException(
        status_code=report_endpoint_service.to_http_status(error),
        detail={"code": error.code, "message": str(error)},
    )


def _client(principal: Principal) -> SupabaseUserClient:
    if not principal.access_token:
        raise HTTPException(status_code=401, detail="Missing user access token.")
    return SupabaseUserClient(principal.access_token)


@router.get("/templates", response_model=list[TrainingTemplateDTO])
def get_templates(principal: Principal = Depends(require_role("platform"))) -> list[TrainingTemplateDTO]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        return [template_from_row(row) for row in _client(principal).select("training_templates", "select=*&order=title.asc")]
    return mock_store.training_templates


@router.post("/templates", response_model=TrainingTemplateDTO)
def create_template(principal: Principal = Depends(require_role("platform"))) -> TrainingTemplateDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        raise HTTPException(status_code=501, detail="Supabase template creation is not implemented in this phase.")
    template = mock_store.training_templates[0].model_copy(deep=True)
    template.id = f"template-mock-created-{int(datetime.now(timezone.utc).timestamp())}"
    template.title = "Mock Created Template"
    template.status = "draft"
    return template


@router.get("/companies", response_model=list[CompanyDTO])
def get_companies(principal: Principal = Depends(require_role("platform"))) -> list[CompanyDTO]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        rows = client.select("companies", "select=*&order=name.asc")
        companies = []
        for row in rows:
            members = client.select("company_members", f"select=user_id&company_id=eq.{row['id']}&status=eq.active")
            assignments = client.select("company_training_assignments", f"select=template_id&company_id=eq.{row['id']}&status=eq.active")
            companies.append(company_from_row(row, learner_count=len(members), template_ids=sorted({item["template_id"] for item in assignments})))
        return companies
    return mock_store.companies


@router.post("/companies", response_model=CompanyDTO)
def create_company(principal: Principal = Depends(require_role("platform"))) -> CompanyDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        raise HTTPException(status_code=501, detail="Supabase company creation is not implemented in this phase.")
    return CompanyDTO(
        id=f"company-mock-{int(datetime.now(timezone.utc).timestamp())}",
        name="Mock Created Company",
        industry="Mock Industry",
        learnerCount=0,
        assignedTrainingTemplateIds=[],
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/assignments")
def create_assignment(principal: Principal = Depends(require_role("platform"))) -> dict[str, object]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        raise HTTPException(status_code=501, detail="Supabase assignment creation is not implemented in this phase.")
    return {"status": "mock_assigned", "enrollments": [item.model_dump() for item in mock_store.enrollments]}


@router.get("/assignments")
def get_assignments(principal: Principal = Depends(require_role("platform"))) -> list[dict[str, object]]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        rows = _client(principal).select("company_training_assignments", "select=id,template_id,module_id,company_id,status&order=created_at.desc")
        return [
            {
                "id": row["id"],
                "templateId": row["template_id"],
                "moduleId": row["module_id"],
                "companyId": row["company_id"],
                "status": row["status"],
            }
            for row in rows
        ]
    return [
        {
            "id": "assignment-demo",
            "templateId": "template-sales-communication",
            "companyId": "company-demo",
            "status": "active",
        }
    ]


@router.get("/reports/aggregate", response_model=PlatformAggregateReportDTO)
def get_platform_aggregate_report(
    template_id: str | None = Query(default=None, alias="templateId"),
    company_id: str | None = Query(default=None, alias="companyId"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    principal: Principal = Depends(require_role("platform")),
) -> PlatformAggregateReportDTO:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        companies = client.select("companies", "select=id")
        templates = client.select("training_templates", "select=id")
        sessions = client.select("training_sessions", "select=id,status")
        reports = client.select("reports", "select=overall_score")
        scores = [row["overall_score"] for row in reports if row.get("overall_score") is not None]
        from app.schemas.dtos import ReportCoverageDTO, ReportProviderCostSummaryDTO

        return PlatformAggregateReportDTO(
            id="platform-aggregate-supabase",
            sourceScoringSchemaVersions=["1.0"],
            generatedAt="",
            companyCount=len(companies),
            trainingTemplateCount=len(templates),
            sessionSummary=ReportCoverageDTO(
                scoredSessionCount=len(reports),
                totalSessionCount=len(sessions),
                scoringCoverage=(len(reports) / len(sessions)) if sessions else 0,
            ),
            aggregateScoreSummary={
                "averageOverallScore": round(sum(scores) / len(scores), 2) if scores else None,
                "reportCount": len(reports),
            },
            dimensionTrends=[],
            skillTrends=[],
            reportCoverage=ReportCoverageDTO(scoredSessionCount=len(reports), totalSessionCount=len(sessions), scoringCoverage=(len(reports) / len(sessions)) if sessions else 0),
            providerCostSummary=ReportProviderCostSummaryDTO(),
        )
    try:
        return report_endpoint_service.get_platform_aggregate_report(
            template_id=template_id,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ReportGenerationError as error:
        raise_report_http_error(error)


@router.get("/usage")
def get_platform_usage(principal: Principal = Depends(require_role("platform"))) -> dict[str, object]:
    if get_database_mode() == DatabaseMode.SUPABASE:
        client = _client(principal)
        companies = client.select("companies", "select=id")
        sessions = client.select("training_sessions", "select=id")
        rows = client.select("session_usage", "select=*")
        return {
            "scope": "platform",
            "companyCount": len(companies),
            "sessionCount": len(sessions),
            "sessionUsage": usage_from_row(rows[0]).model_dump() if rows else None,
        }
    return {"scope": "platform", "sessionUsage": mock_store.demo_session.usage.model_dump(), "companyCount": len(mock_store.companies)}
