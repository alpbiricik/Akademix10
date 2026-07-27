import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function PlatformIndexPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect target="/platform/dashboard" title="Platform route moved" description="The platform workspace now starts at /platform/dashboard." />
    </AppShell>
  );
}
