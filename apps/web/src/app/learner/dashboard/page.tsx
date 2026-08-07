import Link from "next/link";
import { ArrowRight, ClipboardList, PlayCircle } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { SkillRadar } from "@/components/dashboard/skill-radar";
import { SessionSummaryCard } from "@/components/dashboard/session-summary-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnerDashboardSummary, getLearnerStructuredReport, getLearnerTrainings } from "@/lib/adapters/learnerAdapter";
import { getSession } from "@/lib/adapters/sessionAdapter";
import type { TrainingSession } from "@/lib/state-machine/types";

export const dynamic = "force-dynamic";

export default async function LearnerDashboardPage() {
  const [summary, assignedTrainings, report, session] = await Promise.all([
    getLearnerDashboardSummary(),
    getLearnerTrainings(),
    getLearnerStructuredReport("demo-session-1"),
    getSession("demo-session-1"),
  ]);
  const skillScores = (report?.skillSummaries ?? []).map((score) => ({
    skill: score.skill,
    score: score.averageScore ?? 0,
    delta: score.averageDelta,
  }));
  const primaryTraining = assignedTrainings[0];
  const trainingTitle = primaryTraining && "title" in primaryTraining ? primaryTraining.title : "Assigned training";
  const trainingDuration = primaryTraining && "durationMin" in primaryTraining ? primaryTraining.durationMin : 40;
  const stateCount = primaryTraining && "stateIds" in primaryTraining ? primaryTraining.stateIds.length : 21;

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Learner workspace</p>
            <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h1 className="text-3xl font-semibold">Welcome back</h1>
                <p className="mt-2 max-w-2xl text-slate-600">Your assigned training is ready. Continue your guided roleplay journey and track personal skill progress.</p>
              </div>
              <Link href={`/learner/session/${summary.activeSessionId}`} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
                Start Training
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </section>
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <Card className="rounded-lg border-slate-200">
              <CardHeader><CardTitle>Assigned training</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                  <p className="font-semibold">{trainingTitle}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    {trainingDuration} min, {stateCount} states, controlled avatar usage, and final AI feedback.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link href={`/learner/session/${summary.activeSessionId}`} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
                    <PlayCircle className="h-4 w-4" />
                    Continue Training
                  </Link>
                  <Link href={`/learner/sessions/${summary.reportSessionId}/report`} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-sm font-medium text-slate-900 shadow-xs transition hover:bg-slate-100">
                    <ClipboardList className="h-4 w-4" />
                    View Report
                  </Link>
                </div>
              </CardContent>
            </Card>
            <Card className="rounded-lg border-slate-200">
              <CardHeader><CardTitle>Personal skill progress</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <SkillRadar scores={skillScores} />
                {skillScores.map((score) => (
                  <div key={score.skill} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                    <span className="font-medium">{score.skill}</span>
                    <span className="text-slate-600">{score.score}/100</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
          {isTrainingSession(session) ? <SessionSummaryCard session={session} /> : null}
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}

function isTrainingSession(value: unknown): value is TrainingSession {
  return Boolean(value && typeof value === "object" && "completedStateIds" in value && "usage" in value);
}
