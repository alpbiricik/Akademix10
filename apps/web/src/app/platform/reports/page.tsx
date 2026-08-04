import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { PlatformReportsWorkspace } from "@/components/reports/report-workspaces";

export default function PlatformReportsPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <PlatformReportsWorkspace />
      </ProtectedRoute>
    </AppShell>
  );
}
