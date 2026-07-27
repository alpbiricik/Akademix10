import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function TrainerPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect target="/platform/templates" title="Trainer route deprecated" description="Trainer is no longer a separate role. Template work now lives under /platform/templates." />
    </AppShell>
  );
}
