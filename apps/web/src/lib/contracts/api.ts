import type { ContractRole } from "@/lib/contracts/access";

export type ApiMethod = "GET" | "POST" | "PATCH";

export interface ApiEndpointContract {
  method: ApiMethod;
  path: string;
  description: string;
  requestTypeName: string;
  responseTypeName: string;
  requiredRole: ContractRole | readonly ContractRole[];
}

export const API_ENDPOINTS = {
  auth: [
    {
      method: "GET",
      path: "/me",
      description: "Return the authenticated user profile and tenant context.",
      requestTypeName: "None",
      responseTypeName: "UserDTO",
      requiredRole: ["platform", "company", "learner"],
    },
  ],
  platform: [
    {
      method: "GET",
      path: "/platform/templates",
      description: "List global training templates managed by AkademX10 platform users.",
      requestTypeName: "PlatformTemplateListRequest",
      responseTypeName: "TrainingTemplateDTO[]",
      requiredRole: "platform",
    },
    {
      method: "POST",
      path: "/platform/templates",
      description: "Create a global training template with modules and state drafts.",
      requestTypeName: "CreateTrainingTemplateRequest",
      responseTypeName: "TrainingTemplateDTO",
      requiredRole: "platform",
    },
    {
      method: "GET",
      path: "/platform/companies",
      description: "List customer companies visible to platform operators.",
      requestTypeName: "PlatformCompanyListRequest",
      responseTypeName: "CompanyDTO[]",
      requiredRole: "platform",
    },
    {
      method: "POST",
      path: "/platform/companies",
      description: "Create a customer company record.",
      requestTypeName: "CreateCompanyRequest",
      responseTypeName: "CompanyDTO",
      requiredRole: "platform",
    },
    {
      method: "POST",
      path: "/platform/assignments",
      description: "Assign a platform template or module to a customer company.",
      requestTypeName: "CreateCompanyTrainingAssignmentRequest",
      responseTypeName: "EnrollmentDTO[]",
      requiredRole: "platform",
    },
  ],
  company: [
    {
      method: "GET",
      path: "/company/trainings",
      description: "List trainings assigned to the current company tenant.",
      requestTypeName: "CompanyTrainingListRequest",
      responseTypeName: "TrainingTemplateDTO[]",
      requiredRole: "company",
    },
    {
      method: "GET",
      path: "/company/employees",
      description: "List company members and learner enrollment readiness.",
      requestTypeName: "CompanyEmployeeListRequest",
      responseTypeName: "UserDTO[]",
      requiredRole: "company",
    },
    {
      method: "GET",
      path: "/company/reports",
      description: "List reports generated for the current company tenant.",
      requestTypeName: "CompanyReportListRequest",
      responseTypeName: "ReportDTO[]",
      requiredRole: "company",
    },
    {
      method: "GET",
      path: "/company/usage",
      description: "List usage and cost summaries for the current company tenant.",
      requestTypeName: "CompanyUsageListRequest",
      responseTypeName: "SessionUsageDTO[]",
      requiredRole: "company",
    },
  ],
  learner: [
    {
      method: "GET",
      path: "/learner/trainings",
      description: "List assigned trainings for the current learner.",
      requestTypeName: "LearnerTrainingListRequest",
      responseTypeName: "EnrollmentDTO[]",
      requiredRole: "learner",
    },
    {
      method: "POST",
      path: "/learner/sessions",
      description: "Start a learner session for an assigned training module.",
      requestTypeName: "CreateTrainingSessionRequest",
      responseTypeName: "TrainingSessionDTO",
      requiredRole: "learner",
    },
    {
      method: "GET",
      path: "/learner/sessions/:sessionId",
      description: "Read the current learner's session state and progress.",
      requestTypeName: "SessionDetailRequest",
      responseTypeName: "TrainingSessionDTO",
      requiredRole: "learner",
    },
    {
      method: "PATCH",
      path: "/learner/sessions/:sessionId/state",
      description: "Persist current state progress for the learner session.",
      requestTypeName: "UpdateTrainingSessionStateRequest",
      responseTypeName: "TrainingSessionDTO",
      requiredRole: "learner",
    },
    {
      method: "POST",
      path: "/learner/sessions/:sessionId/answers",
      description: "Submit an answer for the learner session's current state.",
      requestTypeName: "CreateSessionAnswerRequest",
      responseTypeName: "SessionAnswerDTO",
      requiredRole: "learner",
    },
    {
      method: "GET",
      path: "/learner/reports/:sessionId",
      description: "Read the current learner's generated report for a session.",
      requestTypeName: "LearnerReportRequest",
      responseTypeName: "ReportDTO",
      requiredRole: "learner",
    },
  ],
  usageCost: [
    {
      method: "GET",
      path: "/usage/session/:sessionId",
      description: "Read usage totals for a session in the caller's allowed tenant scope.",
      requestTypeName: "SessionUsageRequest",
      responseTypeName: "SessionUsageDTO",
      requiredRole: "learner",
    },
    {
      method: "POST",
      path: "/usage/session/:sessionId/events",
      description: "Append an auditable session event such as state progress or avatar lifecycle.",
      requestTypeName: "CreateSessionEventLogRequest",
      responseTypeName: "SessionEventLogDTO",
      requiredRole: "learner",
    },
    {
      method: "POST",
      path: "/usage/session/:sessionId/cost-log",
      description: "Append usage metering and estimated cost values for a session.",
      requestTypeName: "CreateSessionCostLogRequest",
      responseTypeName: "SessionCostLogDTO",
      requiredRole: "learner",
    },
  ],
} as const satisfies Record<string, readonly ApiEndpointContract[]>;

export type ApiEndpointGroup = keyof typeof API_ENDPOINTS;
