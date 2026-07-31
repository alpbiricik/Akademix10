import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { SessionAnswerPayload, SessionStateUpdatePayload } from "@/lib/api/types";
import type { StructuredScoringResultDTO, TrainingStateDTO } from "@/lib/contracts/dtos";
import { applyMockSkillImpact, completeCurrentState as completeSessionCurrentState, generateMockFeedback, getCurrentState, moveToNextState as moveSessionToNextState, moveToPreviousState as moveSessionToPreviousState, submitAnswer } from "@/lib/state-machine/engine";
import { createOrResetDemoSession, getSessionById, getStatesForSession, updateStoredSession } from "@/lib/repositories/sessionRepository";
import type { TrainingSession, TrainingState } from "@/lib/state-machine/types";

interface SessionApiResponse {
  session: TrainingSession;
  states: TrainingStateDTO[];
}

interface AnswerApiResponse {
  session: TrainingSession;
  feedback: unknown;
  scoringResult?: StructuredScoringResultDTO;
}

interface NormalizedAnswerResponse {
  session: TrainingSession;
  feedback: unknown;
  scoringResult: StructuredScoringResultDTO | null;
}

export function getSession(sessionId: string): Promise<TrainingSession | null> {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getSessionById(sessionId));
  return apiGet<SessionApiResponse>(`/api/learner/sessions/${sessionId}`, { mockRole: "learner" }).then((response) => response.session);
}

export function getSessionStates(sessionId: string): Promise<TrainingState[]> {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getStatesForSession(sessionId));
  return apiGet<{ states: TrainingState[] }>(`/api/learner/sessions/${sessionId}`, { mockRole: "learner" }).then((response) => response.states);
}

export function updateSessionState(sessionId: string, payload: SessionStateUpdatePayload) {
  if (DATA_SOURCE_MODE === "api") {
    return apiPatch<TrainingSession>(`/api/learner/sessions/${sessionId}/state`, payload, { mockRole: "learner" });
  }

  const session = getSessionById(sessionId);
  const states = getStatesForSession(sessionId);
  if (!session) return Promise.resolve(null);
  const next = payload.action === "next" ? moveSessionToNextState(session, states) : payload.action === "previous" ? moveSessionToPreviousState(session, states) : completeSessionCurrentState(session, states);
  return Promise.resolve(updateStoredSession(next));
}

function buildMockScoringResult(session: TrainingSession, state: TrainingState, feedback: NonNullable<TrainingSession["feedback"][number]>): StructuredScoringResultDTO {
  return {
    schemaVersion: "1.0",
    sessionId: session.id,
    stateId: state.id,
    answerRef: `${session.id}:${state.id}`,
    rubricId: `rubric-${session.templateId}-v1`,
    rubricVersion: "1.0",
    overallScore: feedback.overallScore,
    dimensionScores: feedback.dimensions.map((dimension) => ({
      dimensionId: dimension.label.toLowerCase(),
      name: dimension.label,
      score: dimension.score,
      rationale: "Deterministic local mock feedback.",
    })),
    conciseLearnerFeedback: feedback.feedbackText,
    strengths: ["Acknowledges the scenario.", "Moves toward a practical next step."],
    improvementAreas: [feedback.improvementSuggestion],
    recommendedNextAction: "complete_state",
    skillImpacts: session.skillScores.map((score) => ({ skill: score.skill, delta: score.delta, score: score.score, sourceDimensionIds: [] })),
    guardrailFlags: [],
    providerMetadata: { provider: "mock", model: "frontend-local-mock-v1", attemptCount: 1, fallbackUsed: false, latencyMs: null },
    tokenCostMetadata: { inputTokens: 0, outputTokens: 0, estimatedCostUsd: 0, currency: "USD" },
    generatedAt: feedback.createdAt,
  };
}

export function submitSessionAnswerWithScoring(sessionId: string, payload: SessionAnswerPayload): Promise<NormalizedAnswerResponse | null> {
  if (DATA_SOURCE_MODE === "api") {
    return apiPost<AnswerApiResponse>(`/api/learner/sessions/${sessionId}/answers`, payload, { mockRole: "learner" }).then((response) => ({
      session: response.session,
      feedback: response.feedback,
      scoringResult: response.scoringResult ?? null,
    }));
  }

  const session = getSessionById(sessionId);
  const states = getStatesForSession(sessionId);
  const state = states.find((item) => item.id === payload.stateId);
  if (!session) return Promise.resolve(null);
  const answered = submitAnswer(session, payload.stateId, payload.answerText);
  if (!state) {
    const stored = updateStoredSession(answered);
    return Promise.resolve({ session: stored, feedback: null, scoringResult: null });
  }
  const feedback = generateMockFeedback(state, payload.answerText);
  const impacted = applyMockSkillImpact(answered, feedback);
  const completed = updateStoredSession(completeSessionCurrentState(impacted, states));
  return Promise.resolve({ session: completed, feedback, scoringResult: buildMockScoringResult(completed, state, feedback) });
}

export function submitSessionAnswer(sessionId: string, payload: SessionAnswerPayload) {
  return submitSessionAnswerWithScoring(sessionId, payload).then((response) => response?.session ?? null);
}

export function completeCurrentState(sessionId: string) {
  return updateSessionState(sessionId, { action: "complete" });
}

export function moveToNextStateById(sessionId: string) {
  return updateSessionState(sessionId, { action: "next" });
}

export function moveToPreviousStateById(sessionId: string) {
  return updateSessionState(sessionId, { action: "previous" });
}

export const moveToNextState = moveToNextStateById;
export const moveToPreviousState = moveToPreviousStateById;

export function getCurrentSessionState(sessionId: string) {
  const session = getSessionById(sessionId);
  const states = getStatesForSession(sessionId);
  return session ? getCurrentState(session, states) : null;
}

export function resetDemoSession() {
  if (DATA_SOURCE_MODE === "api") {
    return apiPost<TrainingSession>("/api/learner/sessions", undefined, { mockRole: "learner" });
  }
  return Promise.resolve(createOrResetDemoSession());
}
