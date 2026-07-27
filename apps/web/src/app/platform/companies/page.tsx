import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAllCompanies } from "@/lib/repositories/companyRepository";

export default function PlatformCompaniesPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Customer management</p>
            <h1 className="mt-2 text-3xl font-semibold">Companies</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Platform-only view of customer tenants, assigned trainings, learners, and usage summaries.</p>
          </section>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Demo companies</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {getAllCompanies().map((company, index) => (
                <div key={company.id} className="grid gap-3 rounded-md border border-slate-200 p-4 md:grid-cols-[1fr_auto_auto_auto] md:items-center">
                  <div>
                    <p className="font-semibold">{company.name}</p>
                    <p className="mt-1 text-sm text-slate-600">{company.industry}</p>
                  </div>
                  <Badge variant="outline">{company.learnerCount} learners</Badge>
                  <Badge variant="secondary">{index + 1} assigned trainings</Badge>
                  <Badge className="bg-teal-50 text-teal-800">${(company.learnerCount * 0.74).toFixed(0)} mock usage</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
