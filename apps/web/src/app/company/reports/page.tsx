import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { CompanyReportsWorkspace } from "@/components/reports/report-workspaces";

export default function CompanyReportsPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <CompanyReportsWorkspace />
      </ProtectedRoute>
    </AppShell>
  );
}
