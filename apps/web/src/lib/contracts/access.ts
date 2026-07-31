export type ContractRole = "platform" | "company" | "learner";

export const ROLE_HOME_ROUTES: Record<ContractRole, string> = {
  platform: "/platform/dashboard",
  company: "/company/dashboard",
  learner: "/learner/dashboard",
};

export const ROLE_ALLOWED_ROUTE_PREFIXES: Record<ContractRole, string[]> = {
  platform: ["/platform"],
  company: ["/company"],
  learner: ["/learner"],
};

export interface RoleAccessRule {
  role: ContractRole;
  can: string[];
  cannot: string[];
  tenantScope: "global" | "company" | "self";
}

export const ROLE_ACCESS_RULES: RoleAccessRule[] = [
  {
    role: "platform",
    tenantScope: "global",
    can: [
      "Manage global platform training templates",
      "Manage customer company records",
      "Assign templates and modules to companies",
    ],
    cannot: ["Act as a company administrator without an explicit company context"],
  },
  {
    role: "company",
    tenantScope: "company",
    can: ["Manage own employees", "Manage own enrollments", "View own reports", "View own usage"],
    cannot: ["Access platform routes", "Manage other companies"],
  },
  {
    role: "learner",
    tenantScope: "self",
    can: ["Access own assigned trainings", "Run own sessions", "View own reports"],
    cannot: ["Access company routes", "Access platform routes", "Access other learners' sessions"],
  },
];

export function canAccessRoute(role: ContractRole, pathname: string): boolean {
  return ROLE_ALLOWED_ROUTE_PREFIXES[role].some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function getDefaultRouteForRole(role: ContractRole): string {
  return ROLE_HOME_ROUTES[role];
}
