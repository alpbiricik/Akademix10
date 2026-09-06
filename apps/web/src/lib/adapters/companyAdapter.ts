import { apiGet } from "@/lib/api/client";
import type { CompanyAggregateReportDTO, ReportDTO, TrainingTemplateDTO, UserDTO } from "@/lib/contracts/dtos";

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
  void companyId;
  return apiGet<TrainingTemplateDTO[]>("/api/company/trainings");
}

export function getCompanyEmployees(companyId = "company-demo") {
  void companyId;
  return apiGet<UserDTO[]>("/api/company/employees");
}

export function getCompanyReports() {
  return apiGet<ReportDTO[]>("/api/company/reports");
}

export function getCompanyUsage() {
  return apiGet<unknown>("/api/company/usage");
}

export function getCompanyAggregateReport(filters?: { templateId?: string; dateFrom?: string; dateTo?: string }) {
  const params = new URLSearchParams();
  if (filters?.templateId) params.set("templateId", filters.templateId);
  if (filters?.dateFrom) params.set("dateFrom", filters.dateFrom);
  if (filters?.dateTo) params.set("dateTo", filters.dateTo);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<CompanyAggregateReportDTO>(`/api/company/reports/aggregate${suffix}`);
}
