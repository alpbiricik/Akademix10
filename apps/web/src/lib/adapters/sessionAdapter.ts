import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { SessionAnswerPayload, SessionFinalizePayload, SessionStateUpdatePayload } from "@/lib/api/types";
import type { StructuredScoringResultDTO } from "@/lib/contracts/dtos";
import { applyMockSkillImpact, completeCurrentState as completeSessionCurrentState, generateMockFeedback, getCurrentState, moveToNextState as moveSessionToNextState, moveToPreviousState as moveSessionToPreviousState, submitAnswer } from "@/lib/state-machine/engine";
import { createOrResetDemoSession, getSessionById, getStatesForSession, updateStoredSession } from "@/lib/repositories/sessionRepository";
import { getTrainingById, getTrainingTemplateById } from "@/lib/repositories/trainingRepository";
import type { TrainingModule, TrainingSession, TrainingState, TrainingTemplate } from "@/lib/state-machine/types";

export interface ConversationTurnResponse {
  stateId: string;
  turnNumber: number;
  assistantText: string;
  action: "continue" | "complete";
  conversationComplete: boolean;
  providerMetadata: {
    provider: string;
    model: string;
    attemptCount: number;
    fallbackUsed: boolean;
    latencyMs: number | null;
  };
}

export interface VoiceAudioResponse {
  stateId: string;
  assistantText: string;
  conversationComplete: boolean;
  tts?: {
    audioPayloadBase64?: string | null;
    contentType?: string | null;
  };
}

interface SessionApiResponse {
  session: TrainingSession;
  states: TrainingState[];
  module: TrainingModule;
  template: TrainingTemplate;
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

export interface SessionBundle {
  session: TrainingSession;
  states: TrainingState[];
  module: TrainingModule;
  template: TrainingTemplate;
}

function getMockSessionBundle(sessionId: string): SessionBundle | null {
  const session = getSessionById(sessionId);
  if (!session) return null;
  const states = getStatesForSession(sessionId);
  const trainingModule = getTrainingById(session.moduleId);
  const template = getTrainingTemplateById(session.templateId);
  if (!trainingModule || !template) return null;
  return { session, states, module: trainingModule, template };
}

export function getSessionBundle(sessionId: string): Promise<SessionBundle | null> {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getMockSessionBundle(sessionId));
  return apiGet<SessionApiResponse>(`/api/learner/sessions/${sessionId}`, { mockRole: "learner" }).then((response) => ({
    session: response.session,
    states: response.states,
    module: response.module,
    template: response.template,
  }));
}

export function getSession(sessionId: string): Promise<TrainingSession | null> {
  return getSessionBundle(sessionId).then((response) => response?.session ?? null);
}

export function getSessionStates(sessionId: string): Promise<TrainingState[]> {
  return getSessionBundle(sessionId).then((response) => response?.states ?? []);
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

export function submitConversationTurn(sessionId: string, payload: { stateId: string; learnerText: string }) {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve<ConversationTurnResponse>({
      stateId: payload.stateId,
      turnNumber: 1,
      assistantText: "Bu senaryoda devam edelim. Bir sonraki adimi nasil netlestirirdin?",
      action: "continue",
      conversationComplete: false,
      providerMetadata: { provider: "mock", model: "frontend-conversation-mock-v1", attemptCount: 1, fallbackUsed: false, latencyMs: null },
    });
  }
  return apiPost<ConversationTurnResponse>(`/api/learner/sessions/${sessionId}/conversation-turn`, payload, { mockRole: "learner" });
}

export function startVoiceOpening(sessionId: string, stateId: string) {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve<VoiceAudioResponse>({
      stateId,
      assistantText: "Merhaba. Bu senaryoda musteriyle nasil baslamak istersin?",
      conversationComplete: false,
    });
  }
  return apiPost<VoiceAudioResponse>(`/api/learner/sessions/${sessionId}/voice/opening`, { stateId, learnerText: "" }, { mockRole: "learner" });
}

export function finalizeSession(sessionId: string, payload: SessionFinalizePayload) {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.all(payload.answers.map((answer) => submitSessionAnswerWithScoring(sessionId, answer))).then((responses) => responses.at(-1)?.session ?? getSessionById(sessionId));
  }
  return apiPost<{ session: TrainingSession }>(`/api/learner/sessions/${sessionId}/finalize`, payload, { mockRole: "learner" }).then((response) => response.session);
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
