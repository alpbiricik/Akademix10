from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["platform", "company", "learner"]
TrainingStateType = Literal["intro", "video", "avatar", "question", "roleplay", "reflection", "feedback", "final"]
TrainingSessionStatus = Literal["not_started", "in_progress", "completed"]
ScoringRecommendation = Literal["continue", "retry_state", "review_feedback", "complete_state"]


class AvatarPolicyDTO(BaseModel):
    mode: Literal["lite"] = "lite"
    activeTargetMin: float
    openCloseTarget: int
    bufferedBillableMin: float
    safeBudgetUsd: float


class UserDTO(BaseModel):
    id: str
    name: str
    role: Role
    title: str
    companyId: str | None = None


class CompanyDTO(BaseModel):
    id: str
    name: str
    industry: str
    learnerCount: int
    assignedTrainingTemplateIds: list[str]
    createdAt: str


class TrainingTemplateDTO(BaseModel):
    id: str
    title: str
    description: str
    category: str
    estimatedDurationMin: int
    defaultStateCount: int
    skillTags: list[str]
    status: Literal["draft", "active", "archived"]
    createdBy: str
    version: str
    avatarPolicy: AvatarPolicyDTO


class TrainingModuleDTO(BaseModel):
    id: str
    templateId: str
    title: str
    description: str
    durationMin: int
    stateIds: list[str]
    skillTags: list[str]
    status: Literal["draft", "active", "archived"]


class TrainingStateDTO(BaseModel):
    id: str
    moduleId: str
    order: int
    title: str
    type: TrainingStateType
    estimatedMin: int
    avatarEnabled: bool
    avatarBudgetSec: int
    prompt: str
    rubric: str
    skillTags: list[str]
    completionRule: Literal["viewed", "answered", "manual"]


class SessionAnswerDTO(BaseModel):
    stateId: str
    answerText: str
    submittedAt: str


class FeedbackDimensionDTO(BaseModel):
    label: str
    score: int


class RubricCriterionDTO(BaseModel):
    id: str
    description: str


class RubricDimensionDTO(BaseModel):
    id: str
    name: str
    description: str
    weight: float
    minScore: float = 0
    maxScore: float = 100
    criteria: list[RubricCriterionDTO]
    skillTags: list[str]
    criticalFailure: bool = False


class RubricDTO(BaseModel):
    id: str
    version: str
    templateId: str
    stateIds: list[str]
    dimensions: list[RubricDimensionDTO]
    criticalFailureRules: list[str] = Field(default_factory=list)


class ProviderRequestDTO(BaseModel):
    schemaVersion: str = "1.0"
    sessionId: str
    stateId: str
    answerRef: str
    answerText: str
    statePrompt: str
    rubric: RubricDTO
    maxQueriesPerState: int


class DimensionScoreDTO(BaseModel):
    dimensionId: str
    name: str
    score: float
    rationale: str


class SkillImpactDTO(BaseModel):
    skill: str
    delta: int
    score: int | None = None
    sourceDimensionIds: list[str] = Field(default_factory=list)


class GuardrailFlagDTO(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"]


class ProviderMetadataDTO(BaseModel):
    provider: str
    model: str
    attemptCount: int = 1
    fallbackUsed: bool = False
    latencyMs: int | None = None


class TokenCostMetadataDTO(BaseModel):
    inputTokens: int = 0
    outputTokens: int = 0
    estimatedCostUsd: float = 0
    currency: str = "USD"


class ProviderScoringResponseDTO(BaseModel):
    dimensionScores: list[DimensionScoreDTO]
    conciseLearnerFeedback: str
    strengths: list[str]
    improvementAreas: list[str]
    recommendedNextAction: ScoringRecommendation
    guardrailFlags: list[GuardrailFlagDTO] = Field(default_factory=list)
    providerMetadata: ProviderMetadataDTO
    tokenCostMetadata: TokenCostMetadataDTO = Field(default_factory=TokenCostMetadataDTO)


class StructuredScoringResultDTO(BaseModel):
    schemaVersion: str = "1.0"
    sessionId: str
    stateId: str
    answerRef: str
    rubricId: str
    rubricVersion: str
    overallScore: int
    dimensionScores: list[DimensionScoreDTO]
    conciseLearnerFeedback: str
    strengths: list[str]
    improvementAreas: list[str]
    recommendedNextAction: ScoringRecommendation
    skillImpacts: list[SkillImpactDTO]
    guardrailFlags: list[GuardrailFlagDTO] = Field(default_factory=list)
    providerMetadata: ProviderMetadataDTO
    tokenCostMetadata: TokenCostMetadataDTO = Field(default_factory=TokenCostMetadataDTO)
    generatedAt: str


class SessionFeedbackDTO(BaseModel):
    id: str
    stateId: str
    overallScore: int
    dimensions: list[FeedbackDimensionDTO]
    feedbackText: str
    improvementSuggestion: str
    nextAction: str
    createdAt: str


class SkillScoreDTO(BaseModel):
    skill: str
    score: int
    delta: int


class SessionUsageDTO(BaseModel):
    totalDurationMin: int
    avatarTargetMin: float
    avatarToggleTarget: int
    bufferedAvatarMin: float
    avatarUsedMin: float
    avatarOpenCount: int
    estimatedAvatarCostUsd: float
    safeAvatarCostUsd: float
    estimatedTotalCostUsd: float
    safeBudgetUsd: float


class TrainingSessionDTO(BaseModel):
    id: str
    moduleId: str
    templateId: str
    userId: str
    companyId: str
    currentStateId: str
    completedStateIds: list[str]
    startedAt: str
    updatedAt: str
    completedAt: str | None = None
    status: TrainingSessionStatus
    answers: list[SessionAnswerDTO] = Field(default_factory=list)
    feedback: list[SessionFeedbackDTO] = Field(default_factory=list)
    skillScores: list[SkillScoreDTO] = Field(default_factory=list)
    usage: SessionUsageDTO


class SessionCostLogDTO(BaseModel):
    id: str
    sessionId: str
    companyId: str
    inputTokens: int = 0
    outputTokens: int = 0
    sttMinutes: float = 0
    ttsCharacters: int = 0
    avatarActiveSeconds: int = 0
    avatarOpenCount: int = 0
    bufferedBillableAvatarMin: float = 0
    estimatedCostUsd: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: str


class SessionEventLogDTO(BaseModel):
    id: str
    sessionId: str
    companyId: str
    learnerUserId: str
    stateId: str | None = None
    eventType: Literal["state_started", "answer_submitted", "feedback_generated", "avatar_opened", "avatar_closed", "state_completed", "session_completed"]
    payload: dict[str, Any] = Field(default_factory=dict)
    occurredAt: str


class EnrollmentDTO(BaseModel):
    id: str
    companyId: str
    learnerUserId: str
    assignmentId: str
    templateId: str
    moduleId: str
    status: Literal["assigned", "in_progress", "completed", "expired"]
    assignedAt: str
    dueAt: str | None = None
    completedAt: str | None = None


class ReportDTO(BaseModel):
    id: str
    sessionId: str
    companyId: str
    learnerUserId: str
    completionSummary: str
    skillScores: list[SkillScoreDTO]
    strengths: list[str]
    improvementAreas: list[str]
    actionPlan: list[str]
    createdAt: str
