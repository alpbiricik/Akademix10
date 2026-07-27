import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const employees = [
  ["Aylin Kaya", "Sales", "Enrolled", "62% complete"],
  ["Mert Demir", "Customer Success", "Assigned", "Not started"],
  ["Selin Aras", "Account Management", "Completed", "Report ready"],
  ["Can Yildiz", "Sales", "Enrolled", "35% complete"],
];

export default function CompanyEmployeesPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Employees</p>
            <h1 className="mt-2 text-3xl font-semibold">Employee enrollment preview</h1>
          </section>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Enrollment list</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {employees.map(([name, team, status, completion]) => (
                <div key={name} className="grid gap-3 rounded-md border border-slate-200 p-4 md:grid-cols-[1fr_auto_auto] md:items-center">
                  <div>
                    <p className="font-semibold">{name}</p>
                    <p className="mt-1 text-sm text-slate-600">{team}</p>
                  </div>
                  <Badge variant="secondary">{status}</Badge>
                  <Badge variant="outline">{completion}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
