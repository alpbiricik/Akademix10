import { Users } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AssignedTrainings } from "@/components/company/assigned-trainings";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CompanyTrainingsPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Assigned trainings</p>
            <h1 className="mt-2 text-3xl font-semibold">Company training rollout</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Trainings assigned by AkademX10 appear here for HR enrollment and employee rollout.</p>
          </section>
          <AssignedTrainings />
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle>Employee assignment</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-600">This is UI-only. Real employee assignment will come later.</p>
              <Button type="button" className="bg-slate-950 text-white hover:bg-slate-800">
                <Users className="h-4 w-4" />
                Assign to Employees
              </Button>
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
