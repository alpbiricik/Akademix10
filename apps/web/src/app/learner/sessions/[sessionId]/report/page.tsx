import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { LearnerReportWorkspace } from "@/components/reports/report-workspaces";

export default async function LearnerSessionStructuredReportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <LearnerReportWorkspace sessionId={sessionId} />
      </ProtectedRoute>
    </AppShell>
  );
}
