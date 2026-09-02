import { AssignedTrainings } from "@/components/company/assigned-trainings";
import { AppShell } from "@/components/layout/app-shell";
import { CompanyDashboardClient } from "./dashboard-client";

const links = [
  { title: "Assigned Trainings", href: "/company/trainings" },
  { title: "Employees", href: "/company/employees" },
  { title: "Reports", href: "/company/reports" },
  { title: "Usage & Cost", href: "/company/usage" },
];

export const dynamic = "force-dynamic";

export default function CompanyDashboardPage() {
  return (
    <AppShell>
      <CompanyDashboardClient links={links} assignedTrainingsSlot={<AssignedTrainings />} />
    </AppShell>
  );
}
