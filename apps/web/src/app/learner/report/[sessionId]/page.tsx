import { notFound } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { SkillRadar } from "@/components/dashboard/skill-radar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnerReport } from "@/lib/adapters/learnerAdapter";
import { getSession } from "@/lib/adapters/sessionAdapter";

export default async function LearnerReportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const [session, report] = await Promise.all([getSession(sessionId), getLearnerReport(sessionId)]);
  if (!session || report.sessionId !== sessionId) notFound();

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">My report</p>
            <h1 className="mt-2 text-3xl font-semibold">Stress Management report</h1>
            <p className="mt-2 max-w-3xl text-slate-600">{report.completionSummary}</p>
          </section>
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <Card className="rounded-lg border-slate-200">
              <CardHeader><CardTitle>Skill scores</CardTitle></CardHeader>
              <CardContent><SkillRadar scores={report.skillScores} /></CardContent>
            </Card>
            <Card className="rounded-lg border-slate-200">
              <CardHeader><CardTitle>Personalized action plan</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {report.actionPlan.map((item, index) => (
                  <div key={item} className="rounded-md bg-slate-50 p-3 text-sm"><span className="font-semibold text-teal-700">{index + 1}. </span>{item}</div>
                ))}
              </CardContent>
            </Card>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <ListCard title="Strengths" items={report.strengths} />
            <ListCard title="Improvement areas" items={report.improvementAreas} />
          </div>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.map((item) => <p key={item} className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">{item}</p>)}
      </CardContent>
    </Card>
  );
}
