export type UserRole = "platform" | "company" | "learner";

export interface AuthenticatedUser {
  id: string;
  name: string;
  role: UserRole;
  title: string;
  companyId?: string;
}

export const roleDestinations: Record<UserRole, string> = {
  platform: "/platform/dashboard",
  company: "/company/dashboard",
  learner: "/learner/dashboard",
};

export const roleLabels: Record<UserRole, string> = {
  platform: "Platform",
  company: "Company",
  learner: "Learner",
};
