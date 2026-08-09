from typing import Any

from app.schemas.dtos import (
    AvatarPolicyDTO,
    CompanyDTO,
    ConversationConfigDTO,
    EnrollmentDTO,
    ReportDTO,
    SessionFeedbackDTO,
    SessionUsageDTO,
    SkillScoreDTO,
    TrainingModuleDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    TrainingTemplateDTO,
    UserDTO,
)
from app.services.cost_service import get_default_session_usage


def user_from_row(row: dict[str, Any], company_id: str | None = None) -> UserDTO:
    return UserDTO(
        id=row["id"],
        name=row.get("full_name") or "",
        role=row["role"],
        title=row.get("title") or "",
        companyId=company_id,
    )


def company_from_row(row: dict[str, Any], learner_count: int = 0, template_ids: list[str] | None = None) -> CompanyDTO:
    return CompanyDTO(
        id=row["id"],
        name=row.get("name") or "",
        industry=row.get("industry") or "",
        learnerCount=learner_count,
        assignedTrainingTemplateIds=template_ids or [],
        createdAt=row.get("created_at") or "",
    )


def template_from_row(row: dict[str, Any]) -> TrainingTemplateDTO:
    policy = row.get("avatar_policy") or {}
    return TrainingTemplateDTO(
        id=row["id"],
        title=row.get("title") or "",
        description=row.get("description") or "",
        category=row.get("category") or "",
        estimatedDurationMin=row.get("estimated_duration_min") or 0,
        defaultStateCount=row.get("default_state_count") or 0,
        skillTags=row.get("skill_tags") or [],
        status=row.get("status") or "draft",
        createdBy=row.get("created_by") or "",
        version=row.get("version") or "1.0",
        avatarPolicy=AvatarPolicyDTO(
            activeTargetMin=policy.get("activeTargetMin", 7),
            openCloseTarget=policy.get("openCloseTarget", 10),
            bufferedBillableMin=policy.get("bufferedBillableMin", 8.05),
            safeBudgetUsd=policy.get("safeBudgetUsd", 1.25),
        ),
    )


def module_from_row(row: dict[str, Any], state_ids: list[str]) -> TrainingModuleDTO:
    return TrainingModuleDTO(
        id=row["id"],
        templateId=row["template_id"],
        title=row.get("title") or "",
        description=row.get("description") or "",
        durationMin=row.get("duration_min") or 0,
        stateIds=state_ids,
        skillTags=[],
        status=row.get("status") or "draft",
    )


def _completion_rule(value: Any) -> str:
    if isinstance(value, dict):
        rule = value.get("type")
        if rule in {"viewed", "answered", "manual"}:
            return rule
    return "viewed"


def state_from_row(row: dict[str, Any]) -> TrainingStateDTO:
    rubric = row.get("rubric")
    if isinstance(rubric, dict):
        rubric_text = rubric.get("text") or ""
    else:
        rubric_text = str(rubric or "")
    conversation_config = row.get("conversation_config")
    return TrainingStateDTO(
        id=row["id"],
        moduleId=row["module_id"],
        order=row.get("order_index") or 0,
        title=row.get("title") or "",
        type=row.get("type") or "intro",
        estimatedMin=row.get("estimated_min") or 0,
        avatarEnabled=bool(row.get("avatar_enabled")),
        avatarBudgetSec=row.get("avatar_budget_sec") or 0,
        prompt=row.get("prompt") or "",
        rubric=rubric_text,
        skillTags=row.get("skill_tags") or [],
        completionRule=_completion_rule(row.get("completion_rule")),
        conversationConfig=ConversationConfigDTO.model_validate(conversation_config) if isinstance(conversation_config, dict) else None,
    )


def enrollment_from_row(row: dict[str, Any]) -> EnrollmentDTO:
    status_map = {
        "not_started": "assigned",
        "in_progress": "in_progress",
        "completed": "completed",
        "overdue": "expired",
    }
    return EnrollmentDTO(
        id=row["id"],
        companyId=row["company_id"],
        learnerUserId=row["learner_id"],
        assignmentId=row["assignment_id"],
        templateId=row.get("template_id") or "",
        moduleId=row["module_id"],
        status=status_map.get(row.get("status"), "assigned"),
        assignedAt=row.get("assigned_at") or "",
        completedAt=row.get("completed_at"),
    )


def usage_from_row(row: dict[str, Any] | None) -> SessionUsageDTO:
    if not row:
        return get_default_session_usage()
    return SessionUsageDTO(
        totalDurationMin=int(row.get("total_duration_min") or 0),
        avatarTargetMin=float(row.get("avatar_target_min") or 0),
        avatarToggleTarget=int(row.get("avatar_open_count") or 0),
        bufferedAvatarMin=float(row.get("buffered_avatar_min") or 0),
        avatarUsedMin=float(row.get("avatar_used_min") or 0),
        avatarOpenCount=int(row.get("avatar_open_count") or 0),
        estimatedAvatarCostUsd=float(row.get("estimated_avatar_cost_usd") or 0),
        safeAvatarCostUsd=float(row.get("safe_budget_usd") or 0),
        estimatedTotalCostUsd=float(row.get("estimated_total_cost_usd") or 0),
        safeBudgetUsd=float(row.get("safe_budget_usd") or 0),
    )


def session_from_row(row: dict[str, Any], usage: SessionUsageDTO, answers: list | None = None, feedback: list | None = None, scores: list | None = None) -> TrainingSessionDTO:
    return TrainingSessionDTO(
        id=row["id"],
        moduleId=row["module_id"],
        templateId=row["template_id"],
        userId=row["learner_id"],
        companyId=row["company_id"],
        currentStateId=row.get("current_state_id") or "",
        completedStateIds=row.get("completed_state_ids") or [],
        startedAt=row.get("started_at") or "",
        updatedAt=row.get("updated_at") or "",
        completedAt=row.get("completed_at"),
        status=row.get("status") or "not_started",
        answers=answers or [],
        feedback=feedback or [],
        skillScores=scores or [],
        usage=usage,
    )


def report_from_row(row: dict[str, Any]) -> ReportDTO:
    skill_scores = [
        SkillScoreDTO(skill=item.get("skill", ""), score=item.get("score", 0), delta=item.get("delta", 0))
        for item in row.get("skill_summary") or []
    ]
    return ReportDTO(
        id=row["id"],
        sessionId=row["session_id"],
        companyId=row["company_id"],
        learnerUserId=row["learner_id"],
        completionSummary="Persisted Supabase learner report.",
        skillScores=skill_scores,
        strengths=row.get("strengths") or [],
        improvementAreas=row.get("improvement_areas") or [],
        actionPlan=row.get("action_plan") or [],
        createdAt=row.get("generated_at") or "",
    )
