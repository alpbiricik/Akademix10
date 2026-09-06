import type { TrainingSession, TrainingState } from "@/lib/state-machine/types";
import { sortStatesByOrder } from "@/lib/state-machine/utils";

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
    usage: session.usage,
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
