"use client";

import Link from "next/link";
import { ArrowRight, ClipboardList, PlayCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { SkillRadar } from "@/components/dashboard/skill-radar";
import { SessionSummaryCard } from "@/components/dashboard/session-summary-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnerDashboardSummary, getLearnerStructuredReport, getLearnerTrainings } from "@/lib/adapters/learnerAdapter";
import { getSessionBundle, restartLearnerSession } from "@/lib/adapters/sessionAdapter";
import type { TrainingModule, TrainingSession, TrainingState } from "@/lib/state-machine/types";

type LearnerDashboardSummary = Awaited<ReturnType<typeof getLearnerDashboardSummary>>;
type LearnerTraining = Awaited<ReturnType<typeof getLearnerTrainings>>[number];
type LearnerReport = Awaited<ReturnType<typeof getLearnerStructuredReport>>;

export function LearnerDashboardClient() {
  const [summary, setSummary] = useState<LearnerDashboardSummary | null>(null);
  const [assignedTrainings, setAssignedTrainings] = useState<LearnerTraining[]>([]);
  const [report, setReport] = useState<LearnerReport | null>(null);
  const [session, setSession] = useState<unknown>(null);
  const [module, setModule] = useState<TrainingModule | null>(null);
  const [states, setStates] = useState<TrainingState[]>([]);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getLearnerDashboardSummary()
      .then(async (summaryValue) => {
        if (cancelled) return;
        setSummary(summaryValue);
        const activeId = summaryValue?.activeSessionId || "active";
        const [trainingsValue, reportValue, sessionData] = await Promise.all([
          getLearnerTrainings().catch(() => []),
          getLearnerStructuredReport(activeId).catch(() => null),
          getSessionBundle(activeId).catch(() => null),
        ]);
        if (cancelled) return;
        setAssignedTrainings(trainingsValue);
        setReport(reportValue);
        setSession(sessionData?.session ?? null);
        setModule(sessionData?.module ?? null);
        setStates(sessionData?.states ?? []);
      })
      .catch(() => {
        if (!cancelled) setError("Dashboard data could not be loaded.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const skillScores = useMemo(() => {
    return (report?.skillSummaries ?? []).map((score) => ({
      skill: score.skill,
      score: score.averageScore ?? 0,
      delta: score.averageDelta,
    }));
  }, [report]);

  const primaryTraining = assignedTrainings[0];
  const trainingTitle = module?.title ?? (primaryTraining ? "Leadership Essentials: Effective Feedback Conversations" : "Atanan egitim");
  const trainingDuration = module?.durationMin ?? (isTrainingSession(session) ? session.usage.totalDurationMin : 45);
  const stateCount = isTrainingSession(session) ? session.completedStateIds.length : 0;
  const totalStateCount = states.length || 21;
  const activeSessionId = summary?.activeSessionId ?? "active";
  const reportSessionId = summary?.reportSessionId ?? "active";

  const openTrainingSession = useCallback(async () => {
    setStarting(true);
    try {
      const restarted = await restartLearnerSession();
      const targetSessionId = restarted.id || activeSessionId;
      setSession(restarted);
      setError(null);
      const url = `/learner/session/${targetSessionId}`;
      const width = Math.min(1280, window.screen.availWidth * 0.9);
      const height = Math.min(800, window.screen.availHeight * 0.9);
      const left = (window.screen.availWidth - width) / 2;
      const top = (window.screen.availHeight - height) / 2;
      const features = `popup=yes,width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes,location=no,status=no`;
      window.open(url, "TrainingSessionPopup", features);
    } catch {
      setError("Egitim sifirlanamadi. Eski session acilmadi; lutfen veritabani migration'inin uygulandigini kontrol et.");
    } finally {
      setStarting(false);
    }
  }, [activeSessionId]);


  return (
    <ProtectedRoute allowedRoles={["learner"]}>
      <div className="space-y-6">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Learner workspace</p>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">Welcome back</h1>
              <p className="mt-2 max-w-2xl text-slate-600">Liderlik eğitimin hazır. Başlattığında en güncel eğitim akışı ilk adımdan açılır.</p>
            </div>
            <button onClick={openTrainingSession} disabled={starting} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
              {starting ? "Baslatiliyor..." : "Egitimi Baslat"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </section>
        {error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Atanan egitim</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="font-semibold">{trainingTitle}</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {trainingDuration} dk hedef, {stateCount}/{totalStateCount} adim tamamlandi. Video dersler, AI gorusmeler, vaka/roleplay degerlendirmesi ve final geri bildirimi icerir.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button onClick={openTrainingSession} disabled={starting} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
                  <PlayCircle className="h-4 w-4" />
                  {starting ? "Guncel egitim baslatiliyor..." : "Egitime Devam Et"}
                </button>
                <Link href={`/learner/sessions/${reportSessionId}/report`} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-sm font-medium text-slate-900 shadow-xs transition hover:bg-slate-100">
                  <ClipboardList className="h-4 w-4" />
                  Raporu Gor
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
  );
}

function isTrainingSession(value: unknown): value is TrainingSession {
  return Boolean(value && typeof value === "object" && "completedStateIds" in value && "usage" in value);
}
