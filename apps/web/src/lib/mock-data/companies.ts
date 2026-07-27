import type { Company } from "@/lib/state-machine/types";

export const companies: Company[] = [
  {
    id: "company-demo",
    name: "Northwind Sales Academy",
    industry: "B2B SaaS Sales",
    learnerCount: 128,
    assignedTrainingTemplateIds: ["template-sales-communication", "template-leadership", "template-stress-management"],
    createdAt: "2026-06-28T09:00:00.000Z",
  },
  {
    id: "company-secondary",
    name: "Contoso People Ops",
    industry: "Customer Operations",
    learnerCount: 84,
    assignedTrainingTemplateIds: ["template-project-management", "template-workplace-ethics"],
    createdAt: "2026-07-01T09:00:00.000Z",
  },
];
