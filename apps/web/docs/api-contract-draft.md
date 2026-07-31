# API Contract Draft

This draft documents future FastAPI endpoints. Phase 2B does not implement API routes or frontend API calls.

## Auth

| Method | Path | Required Role | Request Body | Response | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /me | platform, company, or learner | None | UserDTO | Returns authenticated user and tenant context. |

## Platform

| Method | Path | Required Role | Request Body | Response | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /platform/templates | platform | Query filters | TrainingTemplateDTO[] | Lists global templates. |
| POST | /platform/templates | platform | CreateTrainingTemplateRequest | TrainingTemplateDTO | Creates platform-owned template draft. |
| GET | /platform/companies | platform | Query filters | CompanyDTO[] | Lists customer companies. |
| POST | /platform/companies | platform | CreateCompanyRequest | CompanyDTO | Creates a company tenant record. |
| POST | /platform/assignments | platform | CreateCompanyTrainingAssignmentRequest | EnrollmentDTO[] | Assigns templates or modules to companies. |

## Company

| Method | Path | Required Role | Request Body | Response | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /company/trainings | company | Query filters | TrainingTemplateDTO[] | Lists trainings assigned to caller's company. |
| GET | /company/employees | company | Query filters | UserDTO[] | Lists employees for caller's company. |
| GET | /company/reports | company | Query filters | ReportDTO[] | Lists reports for caller's company. |
| GET | /company/usage | company | Query filters | SessionUsageDTO[] | Lists company-scoped usage summaries. |

## Learner

| Method | Path | Required Role | Request Body | Response | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /learner/trainings | learner | Query filters | EnrollmentDTO[] | Lists own assigned trainings. |
| POST | /learner/sessions | learner | CreateTrainingSessionRequest | TrainingSessionDTO | Starts a session for an assigned module. |
| GET | /learner/sessions/:sessionId | learner | None | TrainingSessionDTO | Reads own session state. |
| PATCH | /learner/sessions/:sessionId/state | learner | UpdateTrainingSessionStateRequest | TrainingSessionDTO | Persists current state progress. |
| POST | /learner/sessions/:sessionId/answers | learner | CreateSessionAnswerRequest | SessionAnswerDTO | Submits an answer for a state. |
| GET | /learner/reports/:sessionId | learner | None | ReportDTO | Reads own generated session report. |

## Usage And Cost

| Method | Path | Required Role | Request Body | Response | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /usage/session/:sessionId | learner | None | SessionUsageDTO | Reads session usage in caller's allowed scope. |
| POST | /usage/session/:sessionId/events | learner | CreateSessionEventLogRequest | SessionEventLogDTO | Appends state, answer, feedback, avatar, or completion events. |
| POST | /usage/session/:sessionId/cost-log | learner | CreateSessionCostLogRequest | SessionCostLogDTO | Appends token, voice, avatar, and estimated cost metering. |

## Access Notes

Platform endpoints require the platform role. Company endpoints require the company role and must be scoped to the caller's company_id. Learner endpoints require the learner role and must be scoped to the caller's user id. Usage and cost endpoints must enforce session ownership and company tenant scope before returning or writing data.
