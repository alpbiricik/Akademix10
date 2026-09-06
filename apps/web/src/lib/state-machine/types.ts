import type { UserRole } from "@/lib/auth-types";

export interface UserProfile {
  id: string;
  name: string;
  role: UserRole;
  title: string;
  companyId?: string | null;
}

export type User = UserProfile & {
  assignedTrainingId?: string;
};

export interface Company {
  id: string;
  name: string;
  industry: string;
  learnerCount: number;
  assignedTrainingTemplateIds: string[];
  createdAt: string;
}

export interface AvatarPolicy {
  mode: "lite";
  activeTargetMin: number;
  openCloseTarget: number;
  bufferedBillableMin: number;
  safeBudgetUsd: number;
}

export interface TrainingTemplate {
  id: string;
  title: string;
  description: string;
  category: string;
  estimatedDurationMin: number;
  defaultStateCount: number;
  skillTags: string[];
  status: "draft" | "active" | "archived";
  createdBy: string;
  version: string;
  avatarPolicy: AvatarPolicy;
}

export interface TrainingModule {
  id: string;
  templateId: string;
  title: string;
  description: string;
  durationMin: number;
  stateIds: string[];
  skillTags: string[];
  status: "draft" | "active" | "archived";
}

export type TrainingStateType =
  | "intro"
  | "video"
  | "avatar"
  | "live_avatar"
  | "question"
  | "roleplay"
  | "reflection"
  | "feedback"
  | "final";

export interface TrainingState {
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
  conversationConfig?: {
    minTurns: number;
    maxTurns: number;
    persona: string;
    scenario: string;
    objective: string;
    conversationInstructions: string;
    allowedTopics: string[];
    completionGuidance: string;
    allowCoaching: boolean;
  } | null;
}

export type TrainingSessionStatus = "not_started" | "in_progress" | "completed";

export interface SessionAnswer {
  stateId: string;
  answerText: string;
  submittedAt: string;
}

export interface SkillScore {
  skill: string;
  score: number;
  delta: number;
}

export interface FeedbackDimension {
  label: string;
  score: number;
}

export interface AIFeedback {
  id: string;
  stateId: string;
  overallScore: number;
  dimensions: FeedbackDimension[];
  feedbackText: string;
  improvementSuggestion: string;
  nextAction: string;
  createdAt: string;
}

export interface SessionUsage {
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
}

export interface TrainingSession {
  id: string;
  moduleId: string;
  templateId: string;
  userId: string;
  companyId: string;
  currentStateId: string;
  completedStateIds: string[];
  startedAt: string;
  updatedAt: string;
  completedAt?: string | null;
  status: TrainingSessionStatus;
  answers: SessionAnswer[];
  feedback: AIFeedback[];
  skillScores: SkillScore[];
  usage: SessionUsage;
}

export interface FinalReport {
  sessionId: string;
  completionSummary: string;
  skillScores: SkillScore[];
  strengths: string[];
  improvementAreas: string[];
  actionPlan: string[];
}
