import type { MockUser, User } from "@/lib/state-machine/types";

export const platformDemoUser: MockUser = {
  id: "user-platform-demo",
  name: "Deniz",
  role: "platform",
  title: "Platform Operator",
  companyId: null,
};

export const companyDemoUser: MockUser = {
  id: "user-company-demo",
  name: "Ece",
  role: "company",
  title: "HR Manager",
  companyId: "company-demo",
};

export const learnerDemoUser: User = {
  id: "user-learner-demo",
  name: "Alp",
  role: "learner",
  title: "Employee",
  companyId: "company-demo",
  assignedTrainingId: "communication-sales-101",
};

export const mockUser = learnerDemoUser;
export const users: User[] = [platformDemoUser, companyDemoUser, learnerDemoUser];
