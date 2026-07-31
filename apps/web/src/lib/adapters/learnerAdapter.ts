import { apiGet, apiPost } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { EnrollmentDTO, ReportDTO, TrainingSessionDTO } from "@/lib/contracts/dtos";
import { mockFinalReport } from "@/lib/mock-data/sessions";
import { mockUser } from "@/lib/mock-data/users";
import { createOrResetDemoSession } from "@/lib/repositories/sessionRepository";
import { getAssignedTrainingsForLearner } from "@/lib/repositories/trainingRepository";

export async function getLearnerDashboardSummary(userId = mockUser.id) {
  const trainings = await getLearnerTrainings(userId);
  return {
    assignedTrainingCount: trainings.length,
    activeSessionId: "demo-session-1",
    reportSessionId: "demo-session-1",
  };
}

export function getLearnerTrainings(userId = mockUser.id) {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getAssignedTrainingsForLearner(userId));
  return apiGet<EnrollmentDTO[]>("/api/learner/trainings", { mockRole: "learner" });
}

export function createLearnerSession() {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(createOrResetDemoSession());
  return apiPost<TrainingSessionDTO>("/api/learner/sessions", undefined, { mockRole: "learner" });
}

export function getLearnerReport(sessionId: string) {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(mockFinalReport);
  return apiGet<ReportDTO>(`/api/learner/reports/${sessionId}`, { mockRole: "learner" });
}
