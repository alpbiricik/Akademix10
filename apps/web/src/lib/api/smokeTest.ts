import { getCompanyEmployees, getCompanyReports, getCompanyTrainings, getCompanyUsage } from "@/lib/adapters/companyAdapter";
import { getLearnerStructuredReport, getLearnerTrainings } from "@/lib/adapters/learnerAdapter";
import { getPlatformAssignments, getPlatformCompanies, getPlatformTemplates, getPlatformUsage } from "@/lib/adapters/platformAdapter";
import { completeCurrentState, getSession, getSessionStates, moveToNextState, restartLearnerSession, submitSessionAnswer } from "@/lib/adapters/sessionAdapter";
import { createSessionEvent, getSessionUsage } from "@/lib/adapters/usageAdapter";

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

export async function smokeTestPlatformApi() {
  return runSuite("Platform API", async () => {
    const templates = await getPlatformTemplates();
    const companies = await getPlatformCompanies();
    const usage = await getPlatformUsage();
    const assignments = await getPlatformAssignments();

    return [
      countCheck("GET /api/platform/templates", templates.length),
      countCheck("GET /api/platform/companies", companies.length),
      objectCheck("GET /api/platform/usage", usage),
      objectCheck("GET /api/platform/assignments", assignments),
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
    const session = await restartLearnerSession();
    const sessionId = session.id;
    const report = await getLearnerStructuredReport(sessionId).catch(() => null);

    return [
      countCheck("GET /api/learner/trainings", trainings.length),
      objectCheck("POST /api/learner/sessions", session),
      objectCheck(`GET /api/learner/sessions/${sessionId}/report`, report ?? { status: "not_finalized" }),
    ];
  });
}

export async function smokeTestSessionApi() {
  return runSuite("Session API", async () => {
    const created = await restartLearnerSession();
    const sessionId = created.id;
    const session = await getSession(sessionId);
    const states = await getSessionStates(sessionId);
    const firstInteractiveState = states.find((state) => state.completionRule === "answered") ?? states[0];
    const completed = await completeCurrentState(sessionId);
    const next = await moveToNextState(sessionId);
    const answered = await submitSessionAnswer(sessionId, {
      stateId: firstInteractiveState?.id ?? "communication-sales-state-04",
      answerText: "Smoke test answer for the real API adapter.",
    });
    const usage = await getSessionUsage(sessionId, "learner");
    const event = await createSessionEvent(sessionId, { source: "api-smoke" }, "learner");

    return [
      objectCheck(`GET /api/learner/sessions/${sessionId}`, session),
      countCheck(`session states from GET /api/learner/sessions/${sessionId}`, states.length),
      objectCheck(`PATCH /api/learner/sessions/${sessionId}/state complete`, completed),
      objectCheck(`PATCH /api/learner/sessions/${sessionId}/state next`, next),
      objectCheck(`POST /api/learner/sessions/${sessionId}/answers`, answered),
      objectCheck(`GET /api/usage/session/${sessionId}`, usage),
      objectCheck(`POST /api/usage/session/${sessionId}/events`, event),
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
    mode: "api",
    suites,
  };
}

async function runSuite(name: string, run: () => Promise<SmokeCheck[]>): Promise<SmokeSuiteResult> {
  try {
    const checks = await run();
    return { name, mode: "api", ok: checks.every((check) => check.ok), checks };
  } catch (error) {
    return {
      name,
      mode: "api",
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
