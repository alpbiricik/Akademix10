import { companies } from "@/lib/mock-data/companies";
import { trainingTemplates } from "@/lib/mock-data/trainingTemplates";

export function getCompanyById(companyId: string) {
  return companies.find((company) => company.id === companyId) ?? null;
}

export function getAllCompanies() {
  return companies;
}

export function getTrainingsAssignedToCompany(companyId: string) {
  const company = getCompanyById(companyId);
  if (!company) return [];
  return trainingTemplates.filter((template) => company.assignedTrainingTemplateIds.includes(template.id));
}
