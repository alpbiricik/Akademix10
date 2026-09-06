import { apiGet, apiPost } from "@/lib/api/client";
import type { UserRole } from "@/lib/auth-types";

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
  void role;
  return apiGet<unknown>(`/api/usage/session/${sessionId}`);
}

export function getUsageSummary(role: UserRole): Promise<UsageSummary> {
  if (role === "platform") return apiGet<UsageApiEnvelope>("/api/platform/usage").then((response) => normalizeUsageSummary(role, response.sessionUsage));
  if (role === "company") return apiGet<UsageApiEnvelope>("/api/company/usage").then((response) => normalizeUsageSummary(role, response.sessionUsage));
  return apiGet<Partial<UsageSummary>>("/api/usage/session/active").then((response) => normalizeUsageSummary(role, response));

}

export function createSessionEvent(sessionId: string, event: unknown, role: UserRole = "learner") {
  void role;
  return apiPost<unknown>(`/api/usage/session/${sessionId}/events`, event);
}

export function createSessionCostLog(sessionId: string, costLog: unknown, role: UserRole = "learner") {
  void role;
  return apiPost<unknown>(`/api/usage/session/${sessionId}/cost-log`, costLog);
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
