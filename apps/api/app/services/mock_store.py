from copy import deepcopy

from app.schemas.dtos import (
    AvatarPolicyDTO,
    CompanyDTO,
    EnrollmentDTO,
    ReportDTO,
    SkillScoreDTO,
    TrainingModuleDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
    TrainingTemplateDTO,
    UserDTO,
)
from app.services.cost_service import get_default_session_usage

NOW = "2026-07-29T09:00:00.000Z"

avatar_policy = AvatarPolicyDTO(
    activeTargetMin=7,
    openCloseTarget=10,
    bufferedBillableMin=8.05,
    safeBudgetUsd=1.25,
)

users = [
    UserDTO(id="user-platform-demo", name="Deniz", role="platform", title="Platform Operator", companyId=None),
    UserDTO(id="user-company-demo", name="Ece", role="company", title="HR Manager", companyId="company-demo"),
    UserDTO(id="user-learner-demo", name="Alp", role="learner", title="Employee", companyId="company-demo"),
]

companies = [
    CompanyDTO(id="company-demo", name="Northwind Sales Academy", industry="B2B SaaS Sales", learnerCount=128, assignedTrainingTemplateIds=["template-sales-communication", "template-leadership", "template-stress-management"], createdAt=NOW),
    CompanyDTO(id="company-secondary", name="Contoso People Ops", industry="Customer Operations", learnerCount=84, assignedTrainingTemplateIds=["template-project-management", "template-workplace-ethics"], createdAt=NOW),
]

training_templates = [
    TrainingTemplateDTO(id="template-leadership", title="Leadership", description="Coaching, feedback, accountability, and team alignment.", category="Leadership", estimatedDurationMin=35, defaultStateCount=18, skillTags=["Coaching", "Feedback", "Accountability"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-project-management", title="Project Management", description="Scope alignment, stakeholder updates, and risk escalation.", category="Project Management", estimatedDurationMin=45, defaultStateCount=20, skillTags=["Planning", "Risk Framing", "Stakeholder Alignment"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-workplace-ethics", title="Workplace Ethics", description="Ethical risk recognition, speak-up practice, and escalation paths.", category="Workplace Ethics", estimatedDurationMin=30, defaultStateCount=16, skillTags=["Judgment", "Courage", "Policy Awareness"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-sales-communication", title="Sales / Customer Communication", description="Consultative communication, objection handling, empathy, and closing.", category="Sales / Customer Communication", estimatedDurationMin=40, defaultStateCount=21, skillTags=["Communication", "Empathy", "Objection Handling", "Closing", "Confidence"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-stress-management", title="Stress Management", description="Pressure awareness, self-regulation, and action planning.", category="Wellbeing", estimatedDurationMin=40, defaultStateCount=18, skillTags=["Self-awareness", "Composure", "Boundary Setting"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
    TrainingTemplateDTO(id="template-onboarding", title="Onboarding", description="Role ramp, culture, process fluency, and first-week confidence.", category="Onboarding", estimatedDurationMin=30, defaultStateCount=14, skillTags=["Role Clarity", "Process Fluency", "Confidence"], status="active", createdBy="user-platform-demo", version="1.0", avatarPolicy=avatar_policy),
]

state_sequence = [
    ("intro", "Welcome and session goals", "Welcome to your AI customer communication roleplay.", "Understands the journey and scoring model.", ["Communication", "Confidence"], False, 0, "viewed"),
    ("video", "Customer context brief", "Short video: a renewal customer is unsure whether the platform is worth the cost.", "Identifies context and conversation objective.", ["Product Knowledge", "Communication"], False, 0, "viewed"),
    ("avatar", "Avatar coach welcome", "LiveAvatar Lite frames the practice standard.", "Receives concise coaching.", ["Confidence"], True, 45, "viewed"),
    ("question", "First response", "Customer says: We are not sure the platform is worth renewing. What is your first response?", "Acknowledges concern and asks discovery.", ["Empathy", "Communication"], False, 0, "answered"),
    ("video", "Value framing lesson", "Connect product value to customer outcomes instead of feature lists.", "Uses outcome language.", ["Product Knowledge", "Closing"], False, 0, "viewed"),
    ("roleplay", "Competitor objection", "Customer: Your competitor is cheaper and promises faster onboarding.", "Handles price and value calmly.", ["Objection Handling", "Confidence"], True, 60, "answered"),
    ("feedback", "Roleplay checkpoint", "Summarize where the response created trust.", "Feedback is behavior-specific.", ["Communication"], False, 0, "manual"),
    ("reflection", "Discovery reflection", "Write two discovery questions for the renewal concern.", "Questions are open-ended.", ["Communication", "Empathy"], False, 0, "answered"),
    ("video", "Proof point lesson", "Use adoption, retention, and time-to-value as proof points.", "Connects proof to outcomes.", ["Product Knowledge"], False, 0, "viewed"),
    ("question", "ROI objection drill", "How would you respond to: I do not see measurable ROI?", "Proposes evidence review.", ["Objection Handling"], False, 0, "answered"),
    ("avatar", "Coach micro-model", "Avatar demonstrates an empathy-to-value response pattern.", "Notices reusable structure.", ["Empathy"], True, 45, "viewed"),
    ("roleplay", "Executive stakeholder", "Customer: My CFO only cares about cost.", "Maps value to business evidence.", ["Closing", "Product Knowledge"], True, 60, "answered"),
    ("feedback", "Stakeholder feedback", "Compare answer against clarity, evidence, and next action.", "Scores are transparent.", ["Communication", "Closing"], False, 0, "manual"),
    ("video", "Closing lesson", "Closing means securing a useful next commitment.", "Understands next-step closing.", ["Closing"], False, 0, "viewed"),
    ("question", "Closing question", "What question would you ask before proposing the next meeting?", "Clarifies decision process.", ["Closing", "Communication"], False, 0, "answered"),
    ("roleplay", "Pricing follow-up", "Customer: Send pricing and I will think about it.", "Guides toward dated follow-up.", ["Closing", "Confidence"], True, 60, "answered"),
    ("reflection", "Personal phrase", "Write one sentence for your next objection conversation.", "Action is specific.", ["Communication"], False, 0, "answered"),
    ("avatar", "Final coaching cue", "Avatar gives one final cue before the action plan.", "Practical coaching.", ["Confidence"], True, 45, "viewed"),
    ("feedback", "Final scoring checkpoint", "Summarize progress and one focus area.", "Connects strengths and growth.", ["Communication"], False, 0, "manual"),
    ("reflection", "Final action plan", "Write your final action plan.", "Action plan is concrete.", ["Action Planning"], False, 0, "answered"),
    ("final", "Final summary", "Session complete. Open your report for next actions.", "Completion and report handoff.", ["Communication"], True, 105, "viewed"),
]

training_states = [
    TrainingStateDTO(
        id=f"communication-sales-state-{index + 1:02}",
        moduleId="communication-sales-101",
        order=index + 1,
        title=title,
        type=state_type,
        estimatedMin=2 if index in {0, 20} else 1 + (index % 3),
        avatarEnabled=avatar_enabled,
        avatarBudgetSec=avatar_budget_sec,
        prompt=prompt,
        rubric=rubric,
        skillTags=skill_tags,
        completionRule=completion_rule,
    )
    for index, (state_type, title, prompt, rubric, skill_tags, avatar_enabled, avatar_budget_sec, completion_rule) in enumerate(state_sequence)
]

training_modules = [
    TrainingModuleDTO(
        id="communication-sales-101",
        templateId="template-sales-communication",
        title="AI Roleplay: Customer Communication",
        description="A 40-minute AI-powered roleplay session for customer empathy, objection handling, and next-step closing.",
        durationMin=40,
        stateIds=[state.id for state in training_states],
        skillTags=["Communication", "Empathy", "Objection Handling", "Product Knowledge", "Closing", "Confidence"],
        status="active",
    )
]

demo_session = TrainingSessionDTO(
    id="demo-session-1",
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
    skillScores=[
        SkillScoreDTO(skill="Communication", score=72, delta=0),
        SkillScoreDTO(skill="Empathy", score=68, delta=0),
        SkillScoreDTO(skill="Objection Handling", score=64, delta=0),
        SkillScoreDTO(skill="Confidence", score=66, delta=0),
    ],
    usage=get_default_session_usage(),
)

sessions = {"demo-session-1": demo_session}

enrollments = [
    EnrollmentDTO(id="enrollment-demo", companyId="company-demo", learnerUserId="user-learner-demo", assignmentId="assignment-demo", templateId="template-sales-communication", moduleId="communication-sales-101", status="in_progress", assignedAt=NOW)
]

demo_report = ReportDTO(
    id="report-demo-session-1",
    sessionId="demo-session-1",
    companyId="company-demo",
    learnerUserId="user-learner-demo",
    completionSummary="Demo customer communication roleplay report.",
    skillScores=[SkillScoreDTO(skill="Communication", score=80, delta=8), SkillScoreDTO(skill="Empathy", score=76, delta=8)],
    strengths=["Acknowledges customer concerns.", "Links value to outcomes."],
    improvementAreas=["Ask one more discovery question.", "Use proof points earlier."],
    actionPlan=["Open with empathy and discovery.", "Close with a dated next step."],
    createdAt=NOW,
)


def clone_session(session_id: str = "demo-session-1") -> TrainingSessionDTO:
    return deepcopy(sessions[session_id])


def get_company_templates(company_id: str = "company-demo") -> list[TrainingTemplateDTO]:
    company = next((item for item in companies if item.id == company_id), companies[0])
    return [template for template in training_templates if template.id in company.assignedTrainingTemplateIds]
