import { AppShell } from "@/components/layout/app-shell";
import { LearnerDashboardClient } from "./dashboard-client";

export const dynamic = "force-dynamic";

export default function LearnerDashboardPage() {
  return (
    <AppShell>
      <LearnerDashboardClient />
    </AppShell>
  );
}
