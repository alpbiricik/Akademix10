import { ProtectedRoute } from "@/components/auth/protected-route";
import { SessionRunner } from "@/components/training/session-runner";

export default async function LearnerSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;

  return (
    <ProtectedRoute allowedRoles={["learner"]}>
      <SessionRunner sessionId={sessionId} />
    </ProtectedRoute>
  );
}
