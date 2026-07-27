import { companies } from "@/lib/mock-data/companies";
import { trainingTemplates } from "@/lib/mock-data/trainingTemplates";
import { communicationSalesStates, trainingModules } from "@/lib/mock-data/trainings";

export function getAllTrainingTemplates() {
  return trainingTemplates;
}

export function getTrainingTemplateById(templateId: string) {
  return trainingTemplates.find((template) => template.id === templateId) ?? null;
}

export function getAllTrainingModules() {
  return trainingModules;
}

export function getTrainingById(trainingId: string) {
  return trainingModules.find((training) => training.id === trainingId) ?? null;
}

export function getTrainingStates(trainingId: string) {
  if (trainingId === "communication-sales-101") return communicationSalesStates;
  return [];
}

export function getAssignedTrainingsForCompany(companyId: string) {
  const company = companies.find((item) => item.id === companyId);
  if (!company) return [];
  return trainingTemplates.filter((template) => company.assignedTrainingTemplateIds.includes(template.id));
}

export function getAssignedTrainingsForLearner(_userId: string) {
  return trainingModules;
}
