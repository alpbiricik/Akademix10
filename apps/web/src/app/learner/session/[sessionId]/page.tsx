import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { SessionRunner } from "@/components/training/session-runner";

export default async function LearnerSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <SessionRunner sessionId={sessionId} />
      </ProtectedRoute>
    </AppShell>
  );
}
