import type { FinalReport, TrainingSession } from "@/lib/state-machine/types";
import { communicationSalesStates } from "@/lib/mock-data/trainings";

export const mockSession: TrainingSession = {
  id: "demo-session-1",
  moduleId: "communication-sales-101",
  templateId: "template-sales-communication",
  userId: "user-learner-demo",
  companyId: "company-demo",
  currentStateId: communicationSalesStates[0].id,
  completedStateIds: [],
  startedAt: "2026-06-28T09:00:00.000Z",
  updatedAt: "2026-06-28T09:00:00.000Z",
  completedAt: null,
  status: "in_progress",
  answers: [],
  feedback: [],
  skillScores: [
    { skill: "Communication", score: 72, delta: 0 },
    { skill: "Empathy", score: 68, delta: 0 },
    { skill: "Objection Handling", score: 64, delta: 0 },
    { skill: "Product Knowledge", score: 70, delta: 0 },
    { skill: "Closing", score: 61, delta: 0 },
    { skill: "Confidence", score: 66, delta: 0 },
  ],
  usage: {
    totalDurationMin: 40,
    avatarTargetMin: 7,
    avatarToggleTarget: 10,
    bufferedAvatarMin: 8.05,
    avatarUsedMin: 0,
    avatarOpenCount: 0,
    estimatedAvatarCostUsd: 0,
    safeAvatarCostUsd: 0.8,
    estimatedTotalCostUsd: 0.8,
    safeBudgetUsd: 1.25,
  },
};

export const trainingSessions: TrainingSession[] = [mockSession];

export const mockFinalReport: FinalReport = {
  sessionId: "demo-session-1",
  completionSummary: "Alp completed the AI Roleplay: Customer Communication module with guided practice, feedback checkpoints, and a practical next-step plan.",
  skillScores: mockSession.skillScores.map((score) => ({ ...score, score: Math.min(100, score.score + 8), delta: 8 })),
  strengths: [
    "Acknowledges customer concerns before recommending a solution.",
    "Connects product value to business outcomes.",
    "Uses clearer next-step closing language.",
  ],
  improvementAreas: [
    "Ask one more discovery question before addressing price.",
    "Use proof points earlier in ROI conversations.",
    "Make stakeholder tradeoffs more explicit.",
  ],
  actionPlan: [
    "Open renewal conversations with one empathy statement and one discovery question.",
    "Prepare two proof points before price-sensitive calls.",
    "Close each call with a dated next step.",
  ],
};
