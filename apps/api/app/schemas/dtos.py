from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["platform", "company", "learner"]
TrainingStateType = Literal["intro", "video", "avatar", "live_avatar", "question", "roleplay", "reflection", "feedback", "final"]
TrainingSessionStatus = Literal["not_started", "in_progress", "completed"]
ScoringRecommendation = Literal["continue", "retry_state", "review_feedback", "complete_state"]
ReportType = Literal["learner_session", "company_aggregate", "platform_aggregate"]
ConversationAction = Literal["continue", "complete"]
ConversationGuardrailDecision = Literal["allow", "redirect", "block"]
STTEventType = Literal["stream_started", "speech_started", "partial_transcript", "final_transcript", "committed_transcript", "utterance_end", "error", "stream_closed"]
TTSEventType = Literal["synthesis_started", "first_audio", "audio_payload", "synthesis_completed", "error"]
ConversationGuardrailReason = Literal[
    "in_scope",
    "off_topic",
    "prompt_injection",
    "instruction_extraction",
    "rubric_extraction",
    "state_violation",
    "unsafe_content",
    "malformed_output",
    "excessive_output_length",
    "persona_escape",
]


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


class ConversationConfigDTO(BaseModel):
    minTurns: int = 1
    maxTurns: int = 3
    language: str = "tr"
    persona: str
    scenario: str
    objective: str
    conversationInstructions: str = ""
    allowedTopics: list[str] = Field(default_factory=list)
    completionGuidance: str = ""
    allowCoaching: bool = False


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
    conversationConfig: ConversationConfigDTO | None = None


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
    inputTokens: int | None = None
    outputTokens: int | None = None


class ConversationTurnDTO(BaseModel):
    turnNumber: int
    learnerText: str
    assistantText: str


class ConversationRequestDTO(BaseModel):
    schemaVersion: str = "1.0"
    sessionId: str
    stateId: str
    turnNumber: int
    language: str = "tr"
    persona: str
    scenario: str
    objective: str
    conversationInstructions: str = ""
    allowedTopics: list[str] = Field(default_factory=list)
    completionGuidance: str = ""
    sanitizedLearnerTurn: str
    temporaryContext: list[ConversationTurnDTO] = Field(default_factory=list)
    minTurns: int = 1
    maxTurns: int = 3


class ConversationResultDTO(BaseModel):
    assistantText: str
    action: ConversationAction
    reasonCode: str | None = None
    providerMetadata: ProviderMetadataDTO


class ConversationGuardrailResultDTO(BaseModel):
    decision: ConversationGuardrailDecision
    reasonCode: ConversationGuardrailReason
    safeText: str
    message: str | None = None


class ConversationTurnRequestDTO(BaseModel):
    stateId: str
    learnerText: str
    textOnly: bool = False
    preparedOpeningId: str | None = Field(default=None, max_length=128)


class ConversationTurnResponseDTO(BaseModel):
    session: TrainingSessionDTO | None = None
    stateId: str
    turnNumber: int
    assistantText: str
    action: ConversationAction
    conversationComplete: bool
    guardrail: ConversationGuardrailResultDTO
    providerMetadata: ProviderMetadataDTO
    tts: TextToSpeechResultDTO | None = None
    avatarSessionActive: bool = False



class SpeechToTextMetadataDTO(BaseModel):
    provider: str
    model: str
    language: str
    confidence: float | None = None
    firstPartialMs: int | None = None
    finalTranscriptMs: int | None = None
    utteranceEndMs: int | None = None
    errorCode: str | None = None


class SpeechToTextEventDTO(BaseModel):
    type: STTEventType
    transcript: str | None = None
    isFinal: bool = False
    speechFinal: bool = False
    metadata: SpeechToTextMetadataDTO


class TextToSpeechMetadataDTO(BaseModel):
    provider: str
    model: str
    voice: str
    language: str
    characterCount: int = 0
    firstAudioMs: int | None = None
    synthesisCompleteMs: int | None = None
    errorCode: str | None = None


class TextToSpeechRequestDTO(BaseModel):
    text: str
    language: str = "tr"
    voice: str = "tr"
    outputFormat: str = "mp3_22050_32"


class TextToSpeechResultDTO(BaseModel):
    audioPayloadBase64: str | None = None
    contentType: str | None = None
    pcmAudioBytes: bytes | None = Field(default=None, exclude=True)
    textFallback: str
    metadata: TextToSpeechMetadataDTO


class VoiceTurnMetricsDTO(BaseModel):
    streamStartedAt: str | None = None
    firstPartialMs: int | None = None
    finalTranscriptMs: int | None = None
    utteranceEndMs: int | None = None
    conversationResponseMs: int | None = None
    firstAudioMs: int | None = None
    synthesisCompleteMs: int | None = None
    speechEndToFirstAudioMs: int | None = None


class VoiceTurnResultDTO(BaseModel):
    stateId: str
    turnNumber: int
    assistantText: str
    action: ConversationAction
    conversationComplete: bool
    guardrail: ConversationGuardrailResultDTO
    conversationProviderMetadata: ProviderMetadataDTO
    sttMetadata: SpeechToTextMetadataDTO
    tts: TextToSpeechResultDTO
    metrics: VoiceTurnMetricsDTO
    avatarSessionActive: bool = False
    avatarDeliveryId: str | None = None


class VoiceOpeningResultDTO(BaseModel):
    stateId: str
    assistantText: str
    conversationComplete: bool = False
    conversationProviderMetadata: ProviderMetadataDTO
    tts: TextToSpeechResultDTO
    metrics: VoiceTurnMetricsDTO
    avatarSessionActive: bool = False
    avatarDeliveryId: str | None = None


class LiveAvatarSessionTokenRequestDTO(BaseModel):
    stateId: str


class LiveAvatarSessionTokenResponseDTO(BaseModel):
    provider: str
    sessionToken: str | None = None
    avatarId: str | None = None
    voiceId: str | None = None
    quality: str = "medium"
    sessionTimeoutSec: int = 600
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveAvatarSessionActionRequestDTO(BaseModel):
    stateId: str
    avatarSessionId: str | None = None
    action: Literal["start", "stop", "speak"]
    text: str | None = None


class LiveAvatarSessionActionResponseDTO(BaseModel):
    status: Literal["created", "started", "stopped", "speaking", "fallback"]
    stateId: str
    avatarSessionId: str | None = None
    activeSeconds: float = 0.0
    errorMessage: str | None = None
    providerMetadata: ProviderMetadataDTO | None = None


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


class ReportReferenceDTO(BaseModel):
    id: str
    label: str | None = None
    version: str | None = None


class ReportCoverageDTO(BaseModel):
    expectedStateCount: int = 0
    evaluatedStateCount: int = 0
    scoredSessionCount: int = 0
    totalSessionCount: int = 0
    scoringCoverage: float = 0
    completionRate: float | None = None
    isPartial: bool = False
    missingStateIds: list[str] = Field(default_factory=list)
    insufficientSample: bool = False


class ReportDimensionSummaryDTO(BaseModel):
    dimensionId: str
    name: str
    averageScore: float
    resultCount: int


class ReportSkillSummaryDTO(BaseModel):
    skill: str
    averageScore: float | None = None
    averageDelta: float
    resultCount: int


class ReportGuardrailSummaryDTO(BaseModel):
    totalFlags: int = 0
    bySeverity: dict[str, int] = Field(default_factory=dict)
    codes: list[str] = Field(default_factory=list)


class ReportProviderCostSummaryDTO(BaseModel):
    providers: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    inputTokens: int = 0
    outputTokens: int = 0
    estimatedCostUsd: float = 0
    currency: str = "USD"


class LearnerSessionReportDTO(BaseModel):
    id: str
    schemaVersion: str = "1.0"
    sourceScoringSchemaVersions: list[str]
    reportType: Literal["learner_session"] = "learner_session"
    generatedAt: str
    sessionId: str
    learner: ReportReferenceDTO
    company: ReportReferenceDTO
    trainingTemplate: ReportReferenceDTO
    trainingModule: ReportReferenceDTO
    sessionStatus: TrainingSessionStatus
    completedAt: str | None = None
    evaluatedStateCount: int
    overallScore: float | None
    dimensionSummaries: list[ReportDimensionSummaryDTO]
    skillSummaries: list[ReportSkillSummaryDTO]
    strengths: list[str]
    improvementAreas: list[str]
    recommendedNextActions: list[ScoringRecommendation]
    guardrailSummary: ReportGuardrailSummaryDTO
    coverage: ReportCoverageDTO
    rubricRefs: list[ReportReferenceDTO]
    providerCostSummary: ReportProviderCostSummaryDTO


class CompanyAggregateReportDTO(BaseModel):
    id: str
    schemaVersion: str = "1.0"
    sourceScoringSchemaVersions: list[str]
    reportType: Literal["company_aggregate"] = "company_aggregate"
    generatedAt: str
    company: ReportReferenceDTO
    trainingTemplate: ReportReferenceDTO | None = None
    filterSummary: dict[str, Any] = Field(default_factory=dict)
    totalAssignedLearnerCount: int | None = None
    completedSessionCount: int
    scoredSessionCount: int
    averageOverallScore: float | None
    dimensionAverages: list[ReportDimensionSummaryDTO]
    skillAverages: list[ReportSkillSummaryDTO]
    strongestDimensions: list[ReportDimensionSummaryDTO]
    developmentPriorityDimensions: list[ReportDimensionSummaryDTO]
    strongestSkills: list[ReportSkillSummaryDTO]
    developmentPrioritySkills: list[ReportSkillSummaryDTO]
    guardrailSummary: ReportGuardrailSummaryDTO
    coverage: ReportCoverageDTO
    providerCostSummary: ReportProviderCostSummaryDTO


class PlatformAggregateReportDTO(BaseModel):
    id: str
    schemaVersion: str = "1.0"
    sourceScoringSchemaVersions: list[str]
    reportType: Literal["platform_aggregate"] = "platform_aggregate"
    generatedAt: str
    companyCount: int
    trainingTemplateCount: int
    sessionSummary: ReportCoverageDTO
    aggregateScoreSummary: dict[str, float | int | None]
    dimensionTrends: list[ReportDimensionSummaryDTO]
    skillTrends: list[ReportSkillSummaryDTO]
    reportCoverage: ReportCoverageDTO
    providerCostSummary: ReportProviderCostSummaryDTO


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


class LearnerSessionDataDTO(BaseModel):
    session: TrainingSessionDTO
    states: list[TrainingStateDTO]
    module: TrainingModuleDTO
    template: TrainingTemplateDTO


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
