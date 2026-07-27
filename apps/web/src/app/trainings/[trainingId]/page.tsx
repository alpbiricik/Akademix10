import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function TrainingDetailPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect title="Training detail moved" description="Training details now live inside role-specific route namespaces." />
    </AppShell>
  );
}
