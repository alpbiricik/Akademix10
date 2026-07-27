import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CompanyReportsPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Company reports</p>
            <h1 className="mt-2 text-3xl font-semibold">Company-level training performance</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Aggregate completion, skill impact, and training performance for customer HR users.</p>
          </section>
          <div className="grid gap-4 md:grid-cols-3">
            <ReportMetric label="Completion rate" value="74%" />
            <ReportMetric label="Average skill impact" value="+8.2" />
            <ReportMetric label="Training performance" value="Healthy" />
          </div>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Report boundary</CardTitle></CardHeader>
            <CardContent className="text-sm leading-6 text-slate-600">
              Company admins see aggregate company reporting here. Individual learner reports remain in the learner namespace.
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}

function ReportMetric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardContent className="p-5">
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-1 text-3xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
