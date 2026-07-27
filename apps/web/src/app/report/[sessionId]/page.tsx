import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default async function ReportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return (
    <AppShell>
      <LegacyRouteRedirect target={`/learner/report/${sessionId}`} title="Report route moved" description="Learner reports now live under /learner/report." />
    </AppShell>
  );
}
