import type {
  TrainingSessionStatus,
  TrainingStateType,
  UserRole,
} from "@/lib/state-machine/types";

export type ISODateTimeString = string;
export type DTORecord = Record<string, unknown>;

export interface UserDTO {
  id: string;
  name: string;
  role: UserRole;
  title: string;
  companyId: string | null;
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface CompanyDTO {
  id: string;
  name: string;
  industry: string;
  learnerCount: number;
  assignedTrainingTemplateIds: string[];
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface TrainingTemplateDTO {
  id: string;
  title: string;
  description: string;
  category: string;
  estimatedDurationMin: number;
  defaultStateCount: number;
  skillTags: string[];
  status: "draft" | "active" | "archived";
  createdByUserId: string;
  version: string;
  avatarPolicy: {
    mode: "lite";
    activeTargetMin: number;
    openCloseTarget: number;
    bufferedBillableMin: number;
    safeBudgetUsd: number;
  };
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface TrainingModuleDTO {
  id: string;
  templateId: string;
  title: string;
  description: string;
  durationMin: number;
  stateIds: string[];
  skillTags: string[];
  status: "draft" | "active" | "archived";
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface TrainingStateDTO {
  id: string;
  moduleId: string;
  order: number;
  title: string;
  type: TrainingStateType;
  estimatedMin: number;
  avatarEnabled: boolean;
  avatarBudgetSec: number;
  prompt: string;
  rubric: string;
  skillTags: string[];
  completionRule: "viewed" | "answered" | "manual";
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface TrainingSessionDTO {
  id: string;
  companyId: string;
  learnerUserId: string;
  templateId: string;
  moduleId: string;
  currentStateId: string;
  completedStateIds: string[];
  status: TrainingSessionStatus;
  startedAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
  completedAt: ISODateTimeString | null;
}

export interface SessionAnswerDTO {
  id: string;
  sessionId: string;
  stateId: string;
  learnerUserId: string;
  answerText: string;
  submittedAt: ISODateTimeString;
}

export interface SessionFeedbackDTO {
  id: string;
  sessionId: string;
  stateId: string;
  overallScore: number;
  dimensions: Array<{
    label: string;
    score: number;
  }>;
  feedbackText: string;
  improvementSuggestion: string;
  nextAction: string;
  generatedBy: "mock" | "ai";
  createdAt: ISODateTimeString;
}

export type ScoringRecommendationDTO = "continue" | "retry_state" | "review_feedback" | "complete_state";

export interface DimensionScoreDTO {
  dimensionId: string;
  name: string;
  score: number;
  rationale: string;
}

export interface SkillImpactDTO {
  skill: string;
  delta: number;
  score: number | null;
  sourceDimensionIds: string[];
}

export interface GuardrailFlagDTO {
  code: string;
  message: string;
  severity: "info" | "warning" | "error";
}

export interface ProviderMetadataDTO {
  provider: string;
  model: string;
  attemptCount: number;
  fallbackUsed: boolean;
  latencyMs: number | null;
}

export interface TokenCostMetadataDTO {
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
  currency: "USD" | string;
}

export interface StructuredScoringResultDTO {
  schemaVersion: string;
  sessionId: string;
  stateId: string;
  answerRef: string;
  rubricId: string;
  rubricVersion: string;
  overallScore: number;
  dimensionScores: DimensionScoreDTO[];
  conciseLearnerFeedback: string;
  strengths: string[];
  improvementAreas: string[];
  recommendedNextAction: ScoringRecommendationDTO;
  skillImpacts: SkillImpactDTO[];
  guardrailFlags: GuardrailFlagDTO[];
  providerMetadata: ProviderMetadataDTO;
  tokenCostMetadata: TokenCostMetadataDTO;
  generatedAt: ISODateTimeString;
}

export interface SkillScoreDTO {
  id: string;
  sessionId: string;
  skill: string;
  score: number;
  delta: number;
  createdAt: ISODateTimeString;
}

export interface SessionUsageDTO {
  id: string;
  sessionId: string;
  companyId: string;
  learnerUserId: string;
  totalDurationMin: number;
  avatarTargetMin: number;
  avatarToggleTarget: number;
  bufferedAvatarMin: number;
  avatarUsedMin: number;
  avatarOpenCount: number;
  estimatedAvatarCostUsd: number;
  safeAvatarCostUsd: number;
  estimatedTotalCostUsd: number;
  safeBudgetUsd: number;
  createdAt: ISODateTimeString;
  updatedAt: ISODateTimeString;
}

export interface SessionCostLogDTO {
  id: string;
  sessionId: string;
  companyId: string;
  inputTokens: number;
  outputTokens: number;
  sttMinutes: number;
  ttsCharacters: number;
  avatarActiveSeconds: number;
  avatarOpenCount: number;
  bufferedBillableAvatarMin: number;
  estimatedCostUsd: number;
  metadata?: DTORecord;
  createdAt: ISODateTimeString;
}

export type SessionEventTypeDTO =
  | "state_started"
  | "answer_submitted"
  | "feedback_generated"
  | "avatar_opened"
  | "avatar_closed"
  | "state_completed"
  | "session_completed";

export interface SessionEventLogDTO {
  id: string;
  sessionId: string;
  companyId: string;
  learnerUserId: string;
  stateId: string | null;
  eventType: SessionEventTypeDTO;
  payload?: DTORecord;
  occurredAt: ISODateTimeString;
}

export interface EnrollmentDTO {
  id: string;
  companyId: string;
  learnerUserId: string;
  assignmentId: string;
  templateId: string;
  moduleId: string;
  status: "assigned" | "in_progress" | "completed" | "expired";
  assignedAt: ISODateTimeString;
  dueAt: ISODateTimeString | null;
  completedAt: ISODateTimeString | null;
}

export interface ReportDTO {
  id: string;
  sessionId: string;
  companyId: string;
  learnerUserId: string;
  completionSummary: string;
  skillScores: SkillScoreDTO[];
  strengths: string[];
  improvementAreas: string[];
  actionPlan: string[];
  createdAt: ISODateTimeString;
}
