from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import Principal, require_role
from app.db.supabase_mappers import report_from_row, template_from_row, usage_from_row, user_from_row
from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import CompanyAggregateReportDTO, ReportDTO, TrainingTemplateDTO, UserDTO

router = APIRouter(prefix="/api/company", tags=["company"])


def _client(principal: Principal) -> SupabaseUserClient:
    if not principal.access_token:
        raise HTTPException(status_code=401, detail="Missing user access token.")
    return SupabaseUserClient(principal.access_token)


@router.get("/trainings", response_model=list[TrainingTemplateDTO])
def get_company_trainings(principal: Principal = Depends(require_role("company"))) -> list[TrainingTemplateDTO]:
    rows = _client(principal).select("training_templates", "select=*&status=eq.active&order=title.asc")
    return [template_from_row(row) for row in rows]


@router.get("/employees", response_model=list[UserDTO])
def get_company_employees(principal: Principal = Depends(require_role("company"))) -> list[UserDTO]:
    client = _client(principal)
    memberships = client.select("company_members", f"select=user_id&company_id=eq.{principal.company_id}&status=eq.active")
    users: list[UserDTO] = []
    for membership in memberships:
        rows = client.select("users", f"select=id,full_name,role,title&id=eq.{membership['user_id']}&limit=1")
        if rows:
            users.append(user_from_row(rows[0], principal.company_id))
    return users


@router.get("/reports/aggregate", response_model=CompanyAggregateReportDTO)
def get_company_aggregate_report(
    template_id: str | None = Query(default=None, alias="templateId"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    principal: Principal = Depends(require_role("company")),
) -> CompanyAggregateReportDTO:
    reports = get_company_reports(principal)
    scores = [score.score for report in reports for score in report.skillScores]
    average = round(sum(scores) / len(scores), 2) if scores else None
    from app.schemas.dtos import ReportCoverageDTO, ReportGuardrailSummaryDTO, ReportProviderCostSummaryDTO, ReportReferenceDTO

    return CompanyAggregateReportDTO(
        id=f"company-aggregate-{principal.company_id}",
        sourceScoringSchemaVersions=["1.0"],
        generatedAt=reports[0].createdAt if reports else "",
        company=ReportReferenceDTO(id=principal.company_id or ""),
        filterSummary={"templateId": template_id, "dateFrom": date_from, "dateTo": date_to},
        completedSessionCount=len(reports),
        scoredSessionCount=len(reports),
        averageOverallScore=average,
        dimensionAverages=[],
        skillAverages=[],
        strongestDimensions=[],
        developmentPriorityDimensions=[],
        strongestSkills=[],
        developmentPrioritySkills=[],
        guardrailSummary=ReportGuardrailSummaryDTO(),
        coverage=ReportCoverageDTO(scoredSessionCount=len(reports), totalSessionCount=len(reports), scoringCoverage=1 if reports else 0),
        providerCostSummary=ReportProviderCostSummaryDTO(),
    )


@router.get("/reports", response_model=list[ReportDTO])
def get_company_reports(principal: Principal = Depends(require_role("company"))) -> list[ReportDTO]:
    rows = _client(principal).select("reports", f"select=*&company_id=eq.{principal.company_id}&order=generated_at.desc")
    return [report_from_row(row) for row in rows]


@router.get("/usage")
def get_company_usage(principal: Principal = Depends(require_role("company"))) -> dict[str, object]:
    client = _client(principal)
    sessions = client.select("training_sessions", f"select=id&company_id=eq.{principal.company_id}")
    usages = []
    for session in sessions:
        rows = client.select("session_usage", f"select=*&session_id=eq.{session['id']}&limit=1")
        if rows:
            usages.append(usage_from_row(rows[0]).model_dump())
    return {"scope": "company", "companyId": principal.company_id, "sessionUsage": usages[0] if usages else None, "sessionCount": len(sessions)}
