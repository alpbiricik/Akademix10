import { MOCK_USER_STORAGE_KEY } from "@/lib/mock-auth";
import { learnerDemoUser, users } from "@/lib/mock-data/users";
import type { MockUser, UserRole } from "@/lib/state-machine/types";

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getCurrentMockUser(): MockUser {
  if (!canUseStorage()) return learnerDemoUser;
  try {
    const value = window.localStorage.getItem(MOCK_USER_STORAGE_KEY);
    if (!value) return learnerDemoUser;
    const parsed = JSON.parse(value) as Partial<MockUser>;
    const user = users.find((item) => item.id === parsed.id);
    return {
      id: typeof parsed.id === "string" ? parsed.id : user?.id ?? learnerDemoUser.id,
      name: typeof parsed.name === "string" ? parsed.name : user?.name ?? learnerDemoUser.name,
      role: parsed.role === "platform" || parsed.role === "company" || parsed.role === "learner" ? parsed.role : user?.role ?? "learner",
      title: typeof parsed.title === "string" ? parsed.title : user?.title ?? learnerDemoUser.title,
      companyId: typeof parsed.companyId === "string" ? parsed.companyId : user?.companyId ?? "company-demo",
    };
  } catch {
    return learnerDemoUser;
  }
}

export function saveCurrentMockUser(user: MockUser) {
  if (canUseStorage()) window.localStorage.setItem(MOCK_USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearCurrentMockUser() {
  if (canUseStorage()) window.localStorage.removeItem(MOCK_USER_STORAGE_KEY);
}

export function getHomeRouteForRole(role: UserRole) {
  if (role === "platform") return "/platform/dashboard";
  if (role === "company") return "/company/dashboard";
  return "/learner/dashboard";
}

export function hasRole(user: MockUser | null, role: UserRole) {
  return user?.role === role;
}
