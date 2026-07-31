import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getCompanyEmployees } from "@/lib/adapters/companyAdapter";

export default async function CompanyEmployeesPage() {
  const employees = await getCompanyEmployees("company-demo");

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
              {employees.map((employee, index) => (
                <div key={employee.id} className="grid gap-3 rounded-md border border-slate-200 p-4 md:grid-cols-[1fr_auto_auto] md:items-center">
                  <div>
                    <p className="font-semibold">{employee.name}</p>
                    <p className="mt-1 text-sm text-slate-600">{employee.title}</p>
                  </div>
                  <Badge variant="secondary">{index % 2 === 0 ? "Enrolled" : "Assigned"}</Badge>
                  <Badge variant="outline">{index % 2 === 0 ? "62% complete" : "Not started"}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
