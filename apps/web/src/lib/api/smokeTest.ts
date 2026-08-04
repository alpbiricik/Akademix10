import { DATA_SOURCE_MODE } from "@/lib/api/config";
import { getCompanyEmployees, getCompanyReports, getCompanyTrainings, getCompanyUsage } from "@/lib/adapters/companyAdapter";
import { getLearnerStructuredReport, getLearnerTrainings } from "@/lib/adapters/learnerAdapter";
import { assignTemplateToCompany, getPlatformCompanies, getPlatformTemplates, getPlatformUsage } from "@/lib/adapters/platformAdapter";
import { completeCurrentState, getSession, getSessionStates, moveToNextState, resetDemoSession, submitSessionAnswer } from "@/lib/adapters/sessionAdapter";
import { createSessionCostLog, createSessionEvent, getSessionUsage } from "@/lib/adapters/usageAdapter";

export interface SmokeCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface SmokeSuiteResult {
  name: string;
  mode: string;
  ok: boolean;
  message?: string;
  checks: SmokeCheck[];
}

const API_MODE_MESSAGE = "API smoke test requires NEXT_PUBLIC_DATA_SOURCE_MODE=api.";
const DEMO_SESSION_ID = "demo-session-1";

export async function smokeTestPlatformApi() {
  return runSuite("Platform API", async () => {
    const templates = await getPlatformTemplates();
    const companies = await getPlatformCompanies();
    const usage = await getPlatformUsage();
    const assignment = await assignTemplateToCompany({ templateId: templates[0]?.id ?? "template-sales-communication", companyId: companies[0]?.id ?? "company-demo" });

    return [
      countCheck("GET /api/platform/templates", templates.length),
      countCheck("GET /api/platform/companies", companies.length),
      objectCheck("GET /api/platform/usage", usage),
      objectCheck("POST /api/platform/assignments", assignment),
    ];
  });
}

export async function smokeTestCompanyApi() {
  return runSuite("Company API", async () => {
    const trainings = await getCompanyTrainings();
    const employees = await getCompanyEmployees();
    const reports = await getCompanyReports();
    const usage = await getCompanyUsage();

    return [
      countCheck("GET /api/company/trainings", trainings.length),
      countCheck("GET /api/company/employees", employees.length),
      countCheck("GET /api/company/reports", reports.length),
      objectCheck("GET /api/company/usage", usage),
    ];
  });
}

export async function smokeTestLearnerApi() {
  return runSuite("Learner API", async () => {
    const trainings = await getLearnerTrainings();
    const session = await resetDemoSession();
    const report = await getLearnerStructuredReport(DEMO_SESSION_ID);

    return [
      countCheck("GET /api/learner/trainings", trainings.length),
      objectCheck("POST /api/learner/sessions", session),
      objectCheck("GET /api/learner/sessions/demo-session-1/report", report),
    ];
  });
}

export async function smokeTestSessionApi() {
  return runSuite("Session API", async () => {
    await resetDemoSession();
    const session = await getSession(DEMO_SESSION_ID);
    const states = await getSessionStates(DEMO_SESSION_ID);
    const firstInteractiveState = states.find((state) => state.completionRule === "answered") ?? states[0];
    const completed = await completeCurrentState(DEMO_SESSION_ID);
    const next = await moveToNextState(DEMO_SESSION_ID);
    const answered = await submitSessionAnswer(DEMO_SESSION_ID, {
      stateId: firstInteractiveState?.id ?? "communication-sales-state-04",
      answerText: "Smoke test answer for the demo API mode adapter.",
    });
    const usage = await getSessionUsage(DEMO_SESSION_ID, "learner");
    const event = await createSessionEvent(DEMO_SESSION_ID, { source: "api-smoke" }, "learner");
    const costLog = await createSessionCostLog(DEMO_SESSION_ID, { source: "api-smoke" }, "learner");

    return [
      objectCheck("GET /api/learner/sessions/demo-session-1", session),
      countCheck("session states from GET /api/learner/sessions/demo-session-1", states.length),
      objectCheck("PATCH /api/learner/sessions/demo-session-1/state complete", completed),
      objectCheck("PATCH /api/learner/sessions/demo-session-1/state next", next),
      objectCheck("POST /api/learner/sessions/demo-session-1/answers", answered),
      objectCheck("GET /api/usage/session/demo-session-1", usage),
      objectCheck("POST /api/usage/session/demo-session-1/events", event),
      objectCheck("POST /api/usage/session/demo-session-1/cost-log", costLog),
    ];
  });
}

export async function smokeTestAllApi() {
  const suites = await Promise.all([
    smokeTestPlatformApi(),
    smokeTestCompanyApi(),
    smokeTestLearnerApi(),
    smokeTestSessionApi(),
  ]);

  return {
    ok: suites.every((suite) => suite.ok),
    mode: DATA_SOURCE_MODE,
    suites,
  };
}

async function runSuite(name: string, run: () => Promise<SmokeCheck[]>): Promise<SmokeSuiteResult> {
  if (DATA_SOURCE_MODE !== "api") {
    return { name, mode: DATA_SOURCE_MODE, ok: false, message: API_MODE_MESSAGE, checks: [] };
  }

  try {
    const checks = await run();
    return { name, mode: DATA_SOURCE_MODE, ok: checks.every((check) => check.ok), checks };
  } catch (error) {
    return {
      name,
      mode: DATA_SOURCE_MODE,
      ok: false,
      checks: [{ name, ok: false, detail: error instanceof Error ? error.message : "Unknown smoke test error." }],
    };
  }
}

function countCheck(name: string, count: number): SmokeCheck {
  return { name, ok: count > 0, detail: `${count} item(s)` };
}

function objectCheck(name: string, value: unknown): SmokeCheck {
  return { name, ok: Boolean(value), detail: value ? "response received" : "empty response" };
}
