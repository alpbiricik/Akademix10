import { mockSession, trainingSessions } from "@/lib/mock-data/sessions";
import { getTrainingStates } from "@/lib/repositories/trainingRepository";
import type { TrainingSession } from "@/lib/state-machine/types";

const SESSION_STORAGE_PREFIX = "akademx10.session.";

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function cloneSession(session: TrainingSession): TrainingSession {
  return JSON.parse(JSON.stringify(session)) as TrainingSession;
}

function sessionSnapshotForBrowserStorage(session: TrainingSession): TrainingSession {
  return { ...session, answers: [] };
}

export function getSessionById(sessionId: string) {
  return loadSessionFromStorage(sessionId) ?? trainingSessions.find((session) => session.id === sessionId) ?? null;
}

export function getStatesForSession(sessionId: string) {
  const session = getSessionById(sessionId);
  return session ? getTrainingStates(session.moduleId) : [];
}

export function createOrResetDemoSession() {
  const session = cloneSession(mockSession);
  saveSessionToStorage(session);
  return session;
}

export function saveSessionToStorage(session: TrainingSession) {
  if (canUseStorage()) window.localStorage.setItem(`${SESSION_STORAGE_PREFIX}${session.id}`, JSON.stringify(sessionSnapshotForBrowserStorage(session)));
  return session;
}

export function loadSessionFromStorage(sessionId: string) {
  if (!canUseStorage()) return null;
  try {
    const value = window.localStorage.getItem(`${SESSION_STORAGE_PREFIX}${sessionId}`);
    return value ? (JSON.parse(value) as TrainingSession) : null;
  } catch {
    return null;
  }
}

export function updateStoredSession(session: TrainingSession) {
  return saveSessionToStorage(session);
}
