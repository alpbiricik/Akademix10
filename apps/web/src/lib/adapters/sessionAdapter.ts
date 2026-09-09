import { ApiError } from "@/lib/api/errors";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type { SessionAnswerPayload, SessionFinalizePayload, SessionStateUpdatePayload } from "@/lib/api/types";
import type {
  LiveAvatarSessionActionRequest,
  LiveAvatarSessionActionResponse,
  LiveAvatarSessionTokenResponse,
  StructuredScoringResultDTO,
} from "@/lib/contracts/dtos";
import { getCurrentState } from "@/lib/state-machine/engine";

import type { TrainingModule, TrainingSession, TrainingState, TrainingTemplate } from "@/lib/state-machine/types";

export interface ConversationTurnResponse {
  session: TrainingSession;
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
  tts?: {
    audioPayloadBase64?: string | null;
    contentType?: string | null;
  };
  avatarSessionActive?: boolean;
}


export interface VoiceAudioResponse {
  stateId: string;
  assistantText: string;
  conversationComplete: boolean;
  tts?: {
    audioPayloadBase64?: string | null;
    contentType?: string | null;
  };
  avatarSessionActive?: boolean;
  avatarDeliveryId?: string | null;
}

export interface VoiceDeliveryResponse {
  status: "sending" | "completed" | "fallback" | "expired" | "cancelled" | "failed" | "text_only";
  audioPayloadBase64?: string | null;
  contentType?: string | null;
  errorCode?: string | null;
}

export function getVoiceDelivery(sessionId: string, deliveryId: string) {
  return apiGet<VoiceDeliveryResponse>(`/api/learner/sessions/${encodeURIComponent(sessionId)}/voice/delivery/${encodeURIComponent(deliveryId)}`);
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

export function getSessionBundle(sessionId: string): Promise<SessionBundle | null> {
  return apiGet<SessionApiResponse>(`/api/learner/sessions/${sessionId}`).then((response) => ({
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
  return apiPatch<TrainingSession>(`/api/learner/sessions/${sessionId}/state`, payload);
}

export function submitSessionAnswerWithScoring(sessionId: string, payload: SessionAnswerPayload): Promise<NormalizedAnswerResponse | null> {
  return apiPost<AnswerApiResponse>(`/api/learner/sessions/${sessionId}/answers`, payload).then((response) => ({
    session: response.session,
    feedback: response.feedback,
    scoringResult: response.scoringResult ?? null,
  }));
}

export function submitSessionAnswer(sessionId: string, payload: SessionAnswerPayload) {
  return submitSessionAnswerWithScoring(sessionId, payload).then((response) => response?.session ?? null);
}

export function submitConversationTurn(sessionId: string, payload: { stateId: string; learnerText: string; textOnly?: boolean }) {
  return apiPost<ConversationTurnResponse>(`/api/learner/sessions/${sessionId}/conversation-turn`, payload);
}

export function startVoiceOpening(sessionId: string, stateId: string, textOnly = false, preparedOpeningId?: string): Promise<VoiceAudioResponse> {
  return apiPost<VoiceAudioResponse>(`/api/learner/sessions/${sessionId}/voice/opening`, { stateId, learnerText: "", textOnly, ...(preparedOpeningId ? { preparedOpeningId } : {}) });
}


export function getAvatarSessionToken(sessionId: string, stateId: string): Promise<LiveAvatarSessionTokenResponse> {
  return apiPost<LiveAvatarSessionTokenResponse>(`/api/learner/sessions/${sessionId}/avatar/token`, { stateId });
}

export function sendAvatarSessionAction(sessionId: string, payload: LiveAvatarSessionActionRequest): Promise<LiveAvatarSessionActionResponse> {
  return apiPost<LiveAvatarSessionActionResponse>(`/api/learner/sessions/${sessionId}/avatar/session`, payload);
}


export function finalizeSession(sessionId: string, payload: SessionFinalizePayload) {
  return apiPost<{ status: string; session: TrainingSession }>(`/api/learner/sessions/${sessionId}/finalize`, payload).then((response) => {
    if (response.status !== "completed" || response.session.status !== "completed") {
      throw new ApiError("Final evaluation is still processing", 409, { detail: { code: "evaluation_processing" } });
    }
    return response.session;
  });
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
  return getSessionBundle(sessionId).then((bundle) => (bundle ? getCurrentState(bundle.session, bundle.states) : null));
}

export function restartLearnerSession() {
  return apiPost<TrainingSession>("/api/learner/sessions/restart");
}

export function cancelVoiceDelivery(sessionId: string, stateId: string) {
  return apiPost(`/api/learner/sessions/${encodeURIComponent(sessionId)}/voice/cancel`, { stateId });
}

export function recoverConversationState(sessionId: string, stateId: string) {
  return apiPost<TrainingSession>(`/api/learner/sessions/${encodeURIComponent(sessionId)}/conversation/recover`, { stateId });
}

export function recordBrowserVoiceMetric(sessionId: string, stateId: string, event: "browser_first_frame" | "browser_playback" | "browser_end_to_end", latencyMs: number) {
  if (!Number.isFinite(latencyMs) || latencyMs < 0 || latencyMs > 600000) return Promise.resolve();
  return apiPost(`/api/learner/sessions/${encodeURIComponent(sessionId)}/voice/metrics`, { stateId, event, metrics: { latency_ms: Math.round(latencyMs) } });
}

export function prepareVoiceOpening(sessionId: string, stateId: string) {
  return apiPost<{ preparedOpeningId: string | null; assistantText: string; errorCode?: string | null }>(`/api/learner/sessions/${encodeURIComponent(sessionId)}/voice/opening/prepare`, { stateId });
}
