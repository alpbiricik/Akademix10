import { AppShell } from "@/components/layout/app-shell";
import { PlatformDashboardClient } from "./dashboard-client";

const links = [
  { title: "Training Templates", href: "/platform/templates" },
  { title: "Companies", href: "/platform/companies" },
  { title: "Assignments", href: "/platform/assignments" },
  { title: "Usage & Cost", href: "/platform/usage" },
];

export const dynamic = "force-dynamic";

export default function PlatformDashboardPage() {
  return (
    <AppShell>
      <PlatformDashboardClient links={links} />
    </AppShell>
  );
}
