import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function CompanyIndexPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect target="/company/dashboard" title="Company route moved" description="The company workspace now starts at /company/dashboard." />
    </AppShell>
  );
}
