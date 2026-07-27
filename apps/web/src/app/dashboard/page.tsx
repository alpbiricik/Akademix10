import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function DashboardPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect title="Dashboard moved" description="Dashboards now live inside role-specific namespaces." />
    </AppShell>
  );
}
