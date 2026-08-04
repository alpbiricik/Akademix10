import { apiGet, apiPost } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { CompanyDTO, PlatformAggregateReportDTO, TrainingTemplateDTO } from "@/lib/contracts/dtos";
import { mockPlatformAggregateReport } from "@/lib/mock-data/reports";
import { getAllCompanies } from "@/lib/repositories/companyRepository";
import { getAllTrainingTemplates } from "@/lib/repositories/trainingRepository";

export const BROWSER_ASSIGNMENTS_STORAGE_KEY = "akademx10.assignedTrainings";

export async function getPlatformDashboardSummary() {
  const [templates, companies, usage] = await Promise.all([
    getPlatformTemplates(),
    getPlatformCompanies(),
    getPlatformUsage(),
  ]);

  return {
    templateCount: templates.length,
    companyCount: companies.length,
    activeAssignmentCount: 7,
    safeBudgetUsd: 1.25,
    usage,
  };
}

export function getPlatformTemplates() {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getAllTrainingTemplates());
  return apiGet<TrainingTemplateDTO[]>("/api/platform/templates", { mockRole: "platform" });
}

export function getPlatformCompanies() {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getAllCompanies());
  return apiGet<CompanyDTO[]>("/api/platform/companies", { mockRole: "platform" });
}

export function getPlatformUsage() {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve({ scope: "platform", mode: "mock", safeBudgetUsd: 1.25, averageSessionCostUsd: 1.18 });
  }
  return apiGet<unknown>("/api/platform/usage", { mockRole: "platform" });
}

export function getPlatformAssignments() {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve([
      {
        id: "assignment-demo",
        templateId: "template-sales-communication",
        companyId: "company-demo",
        status: "active",
      },
    ]);
  }
  return apiGet<unknown>("/api/platform/assignments", { mockRole: "platform" });
}

export function assignTemplateToCompany(input: { templateId: string; companyId: string; moduleId?: string }) {
  if (DATA_SOURCE_MODE === "mock") {
    return Promise.resolve({ status: "mock_assigned", ...input });
  }
  return apiPost<unknown>("/api/platform/assignments", input, { mockRole: "platform" });
}

export function getPlatformAggregateReport(filters?: { templateId?: string; companyId?: string; dateFrom?: string; dateTo?: string }) {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(mockPlatformAggregateReport);
  const params = new URLSearchParams();
  if (filters?.templateId) params.set("templateId", filters.templateId);
  if (filters?.companyId) params.set("companyId", filters.companyId);
  if (filters?.dateFrom) params.set("dateFrom", filters.dateFrom);
  if (filters?.dateTo) params.set("dateTo", filters.dateTo);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<PlatformAggregateReportDTO>(`/api/platform/reports/aggregate${suffix}`, { mockRole: "platform" });
}
