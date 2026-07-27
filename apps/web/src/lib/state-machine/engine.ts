import type { MockAIFeedback, SessionUsage, TrainingSession, TrainingState } from "@/lib/state-machine/types";
import { clampScore, sortStatesByOrder } from "@/lib/state-machine/utils";

const AVATAR_COST_PER_MIN = 0.099;

export function getCurrentState(session: TrainingSession, states: TrainingState[]) {
  const sorted = sortStatesByOrder(states);
  return sorted.find((state) => state.id === session.currentStateId) ?? sorted[0] ?? null;
}

export function getNextState(session: TrainingSession, states: TrainingState[]) {
  const sorted = sortStatesByOrder(states);
  const currentIndex = sorted.findIndex((state) => state.id === session.currentStateId);
  return currentIndex >= 0 ? sorted[currentIndex + 1] ?? null : null;
}

export function getPreviousState(session: TrainingSession, states: TrainingState[]) {
  const sorted = sortStatesByOrder(states);
  const currentIndex = sorted.findIndex((state) => state.id === session.currentStateId);
  return currentIndex > 0 ? sorted[currentIndex - 1] : null;
}

export function canMoveNext(session: TrainingSession, states: TrainingState[]) {
  return Boolean(getNextState(session, states));
}

export function canMovePrevious(session: TrainingSession, states: TrainingState[]) {
  return Boolean(getPreviousState(session, states));
}

export function completeCurrentState(session: TrainingSession, states: TrainingState[]): TrainingSession {
  const current = getCurrentState(session, states);
  if (!current) return session;

  const completedStateIds = Array.from(new Set([...session.completedStateIds, current.id]));
  const completed = completedStateIds.length >= states.length;
  const now = new Date().toISOString();

  return {
    ...session,
    completedStateIds,
    status: completed ? "completed" : "in_progress",
    updatedAt: now,
    completedAt: completed ? now : session.completedAt ?? null,
    usage: calculateMockUsage({ ...session, completedStateIds }, states),
  };
}

export function moveToNextState(session: TrainingSession, states: TrainingState[]): TrainingSession {
  const next = getNextState(session, states);
  if (!next) return session;
  return { ...session, currentStateId: next.id, status: "in_progress", updatedAt: new Date().toISOString() };
}

export function moveToPreviousState(session: TrainingSession, states: TrainingState[]): TrainingSession {
  const previous = getPreviousState(session, states);
  if (!previous) return session;
  return { ...session, currentStateId: previous.id, updatedAt: new Date().toISOString() };
}

export function submitAnswer(session: TrainingSession, stateId: string, answerText: string): TrainingSession {
  const answer = {
    stateId,
    answerText,
    submittedAt: new Date().toISOString(),
  };

  return {
    ...session,
    answers: [...session.answers.filter((item) => item.stateId !== stateId), answer],
    updatedAt: answer.submittedAt,
  };
}

export function generateMockFeedback(state: TrainingState, answerText: string): MockAIFeedback {
  const lengthBonus = answerText.length > 160 ? 8 : answerText.length > 80 ? 5 : 2;
  const roleplayBonus = state.type === "roleplay" ? 4 : 0;
  const base = clampScore(72 + lengthBonus + roleplayBonus + (state.order % 5));

  return {
    id: `feedback-${state.id}-${Date.now()}`,
    stateId: state.id,
    overallScore: base,
    dimensions: [
      { label: "Clarity", score: clampScore(base + 2) },
      { label: "Empathy", score: clampScore(base + (state.skillTags.includes("Empathy") ? 5 : 0)) },
      { label: "Structure", score: clampScore(base - 3) },
      { label: "Confidence", score: clampScore(base + (state.skillTags.includes("Confidence") ? 4 : 1)) },
    ],
    feedbackText: "Strong response. You addressed the context and moved the conversation toward a useful next step.",
    improvementSuggestion: "Make the customer outcome or tradeoff more explicit before offering a recommendation.",
    nextAction: "Ask one concise discovery question, then connect your answer to the customer's stated goal.",
    createdAt: new Date().toISOString(),
  };
}

export function applyMockSkillImpact(session: TrainingSession, feedback: MockAIFeedback): TrainingSession {
  const boost = feedback.overallScore >= 85 ? 4 : feedback.overallScore >= 78 ? 3 : 2;
  const currentSkills = session.skillScores.length ? session.skillScores : [
    { skill: "Communication", score: 72, delta: 0 },
    { skill: "Empathy", score: 68, delta: 0 },
    { skill: "Objection Handling", score: 64, delta: 0 },
    { skill: "Confidence", score: 66, delta: 0 },
  ];

  return {
    ...session,
    feedback: [...session.feedback.filter((item) => item.stateId !== feedback.stateId), feedback],
    skillScores: currentSkills.map((score) => ({
      ...score,
      score: clampScore(score.score + boost),
      delta: score.delta + boost,
    })),
    updatedAt: feedback.createdAt,
  };
}

export function calculateMockUsage(session: TrainingSession, states: TrainingState[]): SessionUsage {
  const completedStates = states.filter((state) => session.completedStateIds.includes(state.id) && state.avatarEnabled);
  const avatarUsedMin = completedStates.reduce((sum, state) => sum + state.avatarBudgetSec / 60, 0);
  const avatarOpenCount = Math.min(session.usage.avatarToggleTarget, completedStates.length);
  return calculateMockCost({ ...session.usage, avatarUsedMin, avatarOpenCount });
}

export function calculateMockCost(usage: SessionUsage): SessionUsage {
  const estimatedAvatarCostUsd = Number((usage.avatarUsedMin * AVATAR_COST_PER_MIN).toFixed(2));
  const safeAvatarCostUsd = Number((usage.bufferedAvatarMin * AVATAR_COST_PER_MIN).toFixed(2));
  return {
    ...usage,
    estimatedAvatarCostUsd,
    safeAvatarCostUsd,
    estimatedTotalCostUsd: Math.min(usage.safeBudgetUsd, Math.max(estimatedAvatarCostUsd, safeAvatarCostUsd)),
  };
}

export function getSessionProgress(session: TrainingSession, states: TrainingState[]) {
  return {
    completed: session.completedStateIds.length,
    total: states.length,
    percent: states.length ? Math.round((session.completedStateIds.length / states.length) * 100) : 0,
  };
}

export function isSessionCompleted(session: TrainingSession, states: TrainingState[]) {
  return session.status === "completed" || (states.length > 0 && session.completedStateIds.length >= states.length);
}
