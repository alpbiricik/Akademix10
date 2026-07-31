import { apiGet, apiPost } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { UserRole } from "@/lib/state-machine/types";
import { getSessionById } from "@/lib/repositories/sessionRepository";

export interface UsageSummary {
  role: UserRole;
  totalDurationMin: number;
  avatarTargetMin: number;
  avatarToggleTarget: number;
  bufferedAvatarMin: number;
  safeBudgetUsd: number;
}

interface UsageApiEnvelope {
  scope?: string;
  sessionUsage?: Partial<UsageSummary>;
}

export function getSessionUsage(sessionId: string, role: UserRole) {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getSessionById(sessionId)?.usage ?? null);
  return apiGet<unknown>(`/api/usage/session/${sessionId}`, { mockRole: role });
}

export function getUsageSummary(role: UserRole): Promise<UsageSummary> {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve({
      role,
      totalDurationMin: 40,
      avatarTargetMin: 7,
      avatarToggleTarget: 10,
      bufferedAvatarMin: 8.05,
      safeBudgetUsd: 1.25,
    });
  }
  if (role === "platform") return apiGet<UsageApiEnvelope>("/api/platform/usage", { mockRole: role }).then((response) => normalizeUsageSummary(role, response.sessionUsage));
  if (role === "company") return apiGet<UsageApiEnvelope>("/api/company/usage", { mockRole: role }).then((response) => normalizeUsageSummary(role, response.sessionUsage));
  return apiGet<Partial<UsageSummary>>("/api/usage/session/demo-session-1", { mockRole: role }).then((response) => normalizeUsageSummary(role, response));
}

export function createSessionEvent(sessionId: string, event: unknown, role: UserRole = "learner") {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve({ id: `mock-event-${Date.now()}`, sessionId, event });
  return apiPost<unknown>(`/api/usage/session/${sessionId}/events`, event, { mockRole: role });
}

export function createSessionCostLog(sessionId: string, costLog: unknown, role: UserRole = "learner") {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve({ id: `mock-cost-log-${Date.now()}`, sessionId, costLog });
  return apiPost<unknown>(`/api/usage/session/${sessionId}/cost-log`, costLog, { mockRole: role });
}

function normalizeUsageSummary(role: UserRole, usage?: Partial<UsageSummary>): UsageSummary {
  return {
    role,
    totalDurationMin: usage?.totalDurationMin ?? 40,
    avatarTargetMin: usage?.avatarTargetMin ?? 7,
    avatarToggleTarget: usage?.avatarToggleTarget ?? 10,
    bufferedAvatarMin: usage?.bufferedAvatarMin ?? 8.05,
    safeBudgetUsd: usage?.safeBudgetUsd ?? 1.25,
  };
}
