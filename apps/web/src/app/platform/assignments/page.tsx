import { Send } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { TrainingAdminWorkspace } from "@/components/admin/training-admin-workspace";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PlatformAssignmentsPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Training assignment</p>
            <h1 className="mt-2 text-3xl font-semibold">Assign templates to companies</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Mock platform flow for choosing a training template, selecting a customer company, and previewing enrollment direction.</p>
          </section>
          <Card className="rounded-lg border-slate-200">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Send className="h-5 w-5 text-teal-700" />
                <CardTitle>Enrollment preview</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Badge variant="outline">Template selected by platform</Badge>
              <Badge variant="outline">Company receives assigned training</Badge>
              <Badge variant="outline">HR enrolls employees later</Badge>
              <Badge className="bg-teal-50 text-teal-800">No backend persistence</Badge>
            </CardContent>
          </Card>
          <TrainingAdminWorkspace />
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
