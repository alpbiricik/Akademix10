import { apiGet } from "@/lib/api/client";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import type { CompanyAggregateReportDTO, ReportDTO, TrainingTemplateDTO, UserDTO } from "@/lib/contracts/dtos";
import { mockFinalReport } from "@/lib/mock-data/sessions";
import { mockCompanyAggregateReport } from "@/lib/mock-data/reports";
import { users } from "@/lib/mock-data/users";
import { getTrainingsAssignedToCompany } from "@/lib/repositories/companyRepository";

export async function getCompanyDashboardSummary(companyId = "company-demo") {
  const [trainings, employees, reports, usage] = await Promise.all([
    getCompanyTrainings(companyId),
    getCompanyEmployees(companyId),
    getCompanyReports(),
    getCompanyUsage(),
  ]);

  return {
    assignedTrainingCount: trainings.length,
    employeeCount: employees.length,
    reportCount: reports.length,
    completionRate: 74,
    averageSkillLift: 8.2,
    usage,
  };
}

export function getCompanyTrainings(companyId = "company-demo") {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(getTrainingsAssignedToCompany(companyId));
  return apiGet<TrainingTemplateDTO[]>("/api/company/trainings", { mockRole: "company" });
}

export function getCompanyEmployees(companyId = "company-demo") {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve(users.filter((user) => user.companyId === companyId));
  return apiGet<UserDTO[]>("/api/company/employees", { mockRole: "company" });
}

export function getCompanyReports() {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve([mockFinalReport]);
  return apiGet<ReportDTO[]>("/api/company/reports", { mockRole: "company" });
}

export function getCompanyUsage() {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve({ scope: "company", mode: "mock" });
  return apiGet<unknown>("/api/company/usage", { mockRole: "company" });
}

export function getCompanyAggregateReport(filters?: { templateId?: string; dateFrom?: string; dateTo?: string }) {
  if (DATA_SOURCE_MODE === "mock") return Promise.resolve({ ...mockCompanyAggregateReport, filterSummary: filters ?? {} });
  const params = new URLSearchParams();
  if (filters?.templateId) params.set("templateId", filters.templateId);
  if (filters?.dateFrom) params.set("dateFrom", filters.dateFrom);
  if (filters?.dateTo) params.set("dateTo", filters.dateTo);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<CompanyAggregateReportDTO>(`/api/company/reports/aggregate${suffix}`, { mockRole: "company" });
}
