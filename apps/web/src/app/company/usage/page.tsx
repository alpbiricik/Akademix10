import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getUsageSummary } from "@/lib/adapters/usageAdapter";

export default async function CompanyUsagePage() {
  const summary = await getUsageSummary("company");
  const rows = [
    ["Sessions completed", "118"],
    ["Estimated cost", "$147.50"],
    ["Avatar usage", `${summary.bufferedAvatarMin ?? 8.05} min buffered`],
    ["Safe budget", `$${(summary.safeBudgetUsd ?? 1.25).toFixed(2)}/session`],
  ];

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Company usage</p>
            <h1 className="mt-2 text-3xl font-semibold">Usage and cost for this company</h1>
          </section>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Mock cost summary</CardTitle></CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {rows.map(([label, value]) => (
                <div key={label} className="rounded-md bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="mt-1 text-2xl font-semibold">{value}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
