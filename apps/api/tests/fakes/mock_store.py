from copy import deepcopy

from app.schemas.dtos import (
    AvatarPolicyDTO,
    CompanyDTO,
    ConversationConfigDTO,
    ReportDTO,
    SkillScoreDTO,
    TrainingModuleDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    TrainingTemplateDTO,
)
from app.services.cost_service import get_default_session_usage

NOW = "2026-07-29T09:00:00.000Z"

avatar_policy = AvatarPolicyDTO(activeTargetMin=7, openCloseTarget=10, bufferedBillableMin=8.05, safeBudgetUsd=1.25)

companies = [
    CompanyDTO(id="company-demo", name="Northwind Sales Academy", industry="B2B SaaS Sales", learnerCount=128, assignedTrainingTemplateIds=["template-sales-communication"], createdAt=NOW),
    CompanyDTO(id="company-secondary", name="Contoso People Ops", industry="Customer Operations", learnerCount=84, assignedTrainingTemplateIds=["template-workplace-ethics"], createdAt=NOW),
]

training_templates = [
    TrainingTemplateDTO(id="template-leadership", title="Leadership", description="Coaching practice.", category="Leadership", estimatedDurationMin=35, defaultStateCount=18, skillTags=["Coaching"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-project-management", title="Project Management", description="Stakeholder practice.", category="Project Management", estimatedDurationMin=45, defaultStateCount=20, skillTags=["Planning"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-workplace-ethics", title="Workplace Ethics", description="Ethics practice.", category="Workplace Ethics", estimatedDurationMin=30, defaultStateCount=16, skillTags=["Judgment"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-sales-communication", title="Sales / Customer Communication", description="Consultative communication.", category="Sales / Customer Communication", estimatedDurationMin=40, defaultStateCount=21, skillTags=["Communication", "Empathy", "Objection Handling", "Closing", "Confidence"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
]

conversation_configs = {
    "roleplay": ConversationConfigDTO(
        minTurns=2,
        maxTurns=3,
        language="tr",
        persona="Skeptical renewal customer",
        scenario="The customer is unsure whether renewing the platform is worth the cost.",
        objective="Learner practices empathy, objection handling, value framing, and next-step closing.",
        conversationInstructions="Stay as the customer. React naturally to the learner.",
        allowedTopics=["communication", "empathy", "objection", "customer", "renewal", "value", "price", "closing", "meeting", "plan"],
        completionGuidance="Complete when the learner offers a useful next step, or at maxTurns.",
    )
}

state_specs = [
    ("intro", "Welcome", "Welcome to your AI customer communication roleplay.", "Understands the journey.", ["Communication"], False, 0, "viewed"),
    ("video", "Brief", "A renewal customer is unsure whether the platform is worth the cost.", "Identifies context.", ["Product Knowledge"], False, 0, "viewed"),
    ("avatar", "Coach welcome", "Live avatar frames the practice standard.", "Receives concise coaching.", ["Confidence"], True, 45, "viewed"),
    ("question", "First response", "Customer says renewal may not be worth it. What is your first response?", "Acknowledges concern and asks discovery.", ["Empathy", "Communication"], False, 0, "answered"),
    ("video", "Value framing", "Connect product value to customer outcomes.", "Uses outcome language.", ["Product Knowledge"], False, 0, "viewed"),
    ("roleplay", "Competitor objection", "Customer: Your competitor is cheaper.", "Handles price and value calmly.", ["Objection Handling", "Confidence"], True, 60, "answered"),
    ("reflection", "Final action plan", "Write your final action plan.", "Action plan is concrete.", ["Action Planning"], False, 0, "answered"),
]

training_states = [
    TrainingStateDTO(
        id=f"communication-sales-state-{index + 1:02}",
        moduleId="communication-sales-101",
        order=index + 1,
        title=title,
        type=state_type,
        estimatedMin=2,
        avatarEnabled=avatar_enabled,
        avatarBudgetSec=avatar_budget_sec,
        prompt=prompt,
        rubric=rubric,
        skillTags=skill_tags,
        completionRule=completion_rule,
        conversationConfig=conversation_configs.get(state_type),
    )
    for index, (state_type, title, prompt, rubric, skill_tags, avatar_enabled, avatar_budget_sec, completion_rule) in enumerate(state_specs)
]

training_modules = [
    TrainingModuleDTO(
        id="communication-sales-101",
        templateId="template-sales-communication",
        title="AI Roleplay: Customer Communication",
        description="AI-powered roleplay session.",
        durationMin=40,
        stateIds=[state.id for state in training_states],
        skillTags=["Communication", "Empathy", "Objection Handling", "Product Knowledge", "Closing", "Confidence"],
        status="active",
    )
]

demo_session = TrainingSessionDTO(
    id="unit-session-1",
    moduleId="communication-sales-101",
    templateId="template-sales-communication",
    userId="user-learner-demo",
    companyId="company-demo",
    currentStateId=training_states[0].id,
    completedStateIds=[],
    startedAt=NOW,
    updatedAt=NOW,
    completedAt=None,
    status="in_progress",
    answers=[],
    feedback=[],
    skillScores=[SkillScoreDTO(skill="Communication", score=72, delta=0)],
    usage=get_default_session_usage(),
)

sessions = {"unit-session-1": deepcopy(demo_session)}

demo_report = ReportDTO(
    id="report-unit-session-1",
    sessionId="unit-session-1",
    companyId="company-demo",
    learnerUserId="user-learner-demo",
    completionSummary="Customer communication roleplay report.",
    skillScores=[SkillScoreDTO(skill="Communication", score=80, delta=8)],
    strengths=["Acknowledges customer concerns."],
    improvementAreas=["Ask one more discovery question."],
    actionPlan=["Open with empathy and discovery."],
    createdAt=NOW,
)


def clone_session(session_id: str = "unit-session-1") -> TrainingSessionDTO:
    if session_id == demo_session.id:
        return deepcopy(demo_session)
    return deepcopy(sessions[session_id])
