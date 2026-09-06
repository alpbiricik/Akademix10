import { apiGet, apiPost } from "@/lib/api/client";
import type { CompanyDTO, PlatformAggregateReportDTO, TrainingTemplateDTO } from "@/lib/contracts/dtos";

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
  return apiGet<TrainingTemplateDTO[]>("/api/platform/templates");
}

export function getPlatformCompanies() {
  return apiGet<CompanyDTO[]>("/api/platform/companies");
}

export function getPlatformUsage() {
  return apiGet<unknown>("/api/platform/usage");
}

export function getPlatformAssignments() {
  return apiGet<unknown>("/api/platform/assignments");
}

export function assignTemplateToCompany(input: { templateId: string; companyId: string; moduleId?: string }) {
  return apiPost<unknown>("/api/platform/assignments", input);
}

export function getPlatformAggregateReport(filters?: { templateId?: string; companyId?: string; dateFrom?: string; dateTo?: string }) {
  const params = new URLSearchParams();
  if (filters?.templateId) params.set("templateId", filters.templateId);
  if (filters?.companyId) params.set("companyId", filters.companyId);
  if (filters?.dateFrom) params.set("dateFrom", filters.dateFrom);
  if (filters?.dateTo) params.set("dateTo", filters.dateTo);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<PlatformAggregateReportDTO>(`/api/platform/reports/aggregate${suffix}`);
}
