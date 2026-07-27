import { LegacyRouteRedirect } from "@/components/auth/legacy-route-redirect";
import { AppShell } from "@/components/layout/app-shell";

export default function TrainingsPage() {
  return (
    <AppShell>
      <LegacyRouteRedirect title="Training catalog moved" description="Training pages now live under the platform, company, or learner route namespace." />
    </AppShell>
  );
}
