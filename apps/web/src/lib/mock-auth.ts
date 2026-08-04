export type MockRole = "platform" | "company" | "learner";

export interface MockUserSession {
  id: string;
  name: string;
  role: MockRole;
  title: string;
  companyId?: string;
}

export const MOCK_USER_STORAGE_KEY = "akademx10.mockUser";

export const roleDestinations: Record<MockRole, string> = {
  platform: "/platform/dashboard",
  company: "/company/dashboard",
  learner: "/learner/dashboard",
};

export const roleLabels: Record<MockRole, string> = {
  platform: "Platform / AkademX10 Team",
  company: "Company / HR Manager",
  learner: "Learner / Employee",
};

export const protectedRoutes: Record<MockRole, string[]> = {
  platform: ["/platform/dashboard", "/platform/templates", "/platform/companies", "/platform/assignments", "/platform/reports", "/platform/usage"],
  company: ["/company/dashboard", "/company/trainings", "/company/employees", "/company/reports", "/company/usage"],
  learner: ["/learner/dashboard", "/learner/trainings", "/learner/session/demo-session-1", "/learner/sessions/demo-session-1/report"],
};

export function parseMockUser(value: string | null): MockUserSession | null {
  if (!value) return null;

  try {
    const parsed = JSON.parse(value) as Partial<MockUserSession> & { role?: unknown };
    const role = normalizeMockRole(parsed.role);
    if (
      typeof parsed.name === "string" &&
      typeof parsed.title === "string" &&
      role
    ) {
      return {
        id: typeof parsed.id === "string" ? parsed.id : getDefaultUserId(role),
        name: parsed.name,
        role,
        title: parsed.title,
        companyId: typeof parsed.companyId === "string" ? parsed.companyId : role === "company" || role === "learner" ? "company-demo" : undefined,
      };
    }
  } catch {
    return null;
  }

  return null;
}

export function isMockRole(value: unknown): value is MockRole {
  return value === "platform" || value === "company" || value === "learner";
}

function normalizeMockRole(value: unknown): MockRole | null {
  if (isMockRole(value)) return value;

  // Active product roles are only platform, company, and learner.
  // These old strings are accepted only to migrate stale localStorage data from
  // earlier prototypes. Login/UI must never expose admin, trainer,
  // platform_admin, or company_admin as real app roles. Remove this tolerance
  // after old browser sessions are no longer relevant.
  if (value === "admin" || value === "trainer" || value === "platform_admin") return "platform";
  if (value === "company_admin") return "company";
  if (value === "user") return "learner";
  return null;
}

function getDefaultUserId(role: MockRole) {
  if (role === "platform") return "user-platform-demo";
  if (role === "company") return "user-company-demo";
  return "user-learner-demo";
}
