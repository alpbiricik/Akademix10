from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import Principal, require_role
from app.db.supabase_mappers import company_from_row, template_from_row, usage_from_row
from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import CompanyDTO, PlatformAggregateReportDTO, TrainingTemplateDTO

router = APIRouter(prefix="/api/platform", tags=["platform"])


def _client(principal: Principal) -> SupabaseUserClient:
    if not principal.access_token:
        raise HTTPException(status_code=401, detail="Missing user access token.")
    return SupabaseUserClient(principal.access_token)


@router.get("/templates", response_model=list[TrainingTemplateDTO])
def get_templates(principal: Principal = Depends(require_role("platform"))) -> list[TrainingTemplateDTO]:
    return [template_from_row(row) for row in _client(principal).select("training_templates", "select=*&order=title.asc")]


@router.post("/templates", response_model=TrainingTemplateDTO)
def create_template(principal: Principal = Depends(require_role("platform"))) -> TrainingTemplateDTO:
    raise HTTPException(status_code=501, detail="Supabase template creation is not implemented.")


@router.get("/companies", response_model=list[CompanyDTO])
def get_companies(principal: Principal = Depends(require_role("platform"))) -> list[CompanyDTO]:
    client = _client(principal)
    rows = client.select("companies", "select=*&order=name.asc")
    companies = []
    for row in rows:
        members = client.select("company_members", f"select=user_id&company_id=eq.{row['id']}&status=eq.active")
        assignments = client.select("company_training_assignments", f"select=template_id&company_id=eq.{row['id']}&status=eq.active")
        companies.append(company_from_row(row, learner_count=len(members), template_ids=sorted({item["template_id"] for item in assignments})))
    return companies


@router.post("/companies", response_model=CompanyDTO)
def create_company(principal: Principal = Depends(require_role("platform"))) -> CompanyDTO:
    raise HTTPException(status_code=501, detail="Supabase company creation is not implemented.")


@router.post("/assignments")
def create_assignment(principal: Principal = Depends(require_role("platform"))) -> dict[str, object]:
    raise HTTPException(status_code=501, detail="Supabase assignment creation is not implemented.")


@router.get("/assignments")
def get_assignments(principal: Principal = Depends(require_role("platform"))) -> list[dict[str, object]]:
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


@router.get("/reports/aggregate", response_model=PlatformAggregateReportDTO)
def get_platform_aggregate_report(
    template_id: str | None = Query(default=None, alias="templateId"),
    company_id: str | None = Query(default=None, alias="companyId"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    principal: Principal = Depends(require_role("platform")),
) -> PlatformAggregateReportDTO:
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


@router.get("/usage")
def get_platform_usage(principal: Principal = Depends(require_role("platform"))) -> dict[str, object]:
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
