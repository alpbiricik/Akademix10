import { apiGet, apiPost } from "@/lib/api/client";
import type { EnrollmentDTO, LearnerSessionReportDTO, StructuredScoringResultDTO, TrainingSessionDTO } from "@/lib/contracts/dtos";

export async function getLearnerDashboardSummary() {
  const trainings = await getLearnerTrainings();
  let activeSessionId = "active";
  try {
    const session = await apiGet<{ session: TrainingSessionDTO }>("/api/learner/sessions/active").then((bundle) => bundle.session);
    if (session?.id) {
      activeSessionId = session.id;
    }
  } catch {
    activeSessionId = "active";
  }
  return {
    assignedTrainingCount: trainings.length,
    activeSessionId,
    reportSessionId: activeSessionId,
  };
}


export function getLearnerTrainings() {
  return apiGet<EnrollmentDTO[]>("/api/learner/trainings");
}

export function createLearnerSession() {
  return apiPost<TrainingSessionDTO>("/api/learner/sessions");
}

export function getLearnerSessionScoringResults(sessionId: string) {
  return apiGet<StructuredScoringResultDTO[]>(`/api/learner/sessions/${sessionId}/scoring-results`);
}

export function getLearnerStructuredReport(sessionId: string) {
  return apiGet<LearnerSessionReportDTO>(`/api/learner/sessions/${sessionId}/report`);
}
