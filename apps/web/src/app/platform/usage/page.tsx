import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getUsageSummary } from "@/lib/adapters/usageAdapter";

export const dynamic = "force-dynamic";

export default async function PlatformUsagePage() {
  const summary = await getUsageSummary("platform");
  const usage = [
    ["Session model", `${summary.totalDurationMin ?? 40} min`],
    ["Avatar target", `${summary.avatarTargetMin ?? 7} min`],
    ["Open/close target", `${summary.avatarToggleTarget ?? 10}`],
    ["Buffered avatar usage", `${summary.bufferedAvatarMin ?? 8.05} min`],
    ["Safe budget", `$${(summary.safeBudgetUsd ?? 1.25).toFixed(2)}/session`],
    ["Completed sessions", "684"],
  ];

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Platform usage</p>
            <h1 className="mt-2 text-3xl font-semibold">Usage and cost overview</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Platform-level cost model for controlled LiveAvatar Lite usage.</p>
          </section>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Cost model</CardTitle></CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {usage.map(([label, value]) => (
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
