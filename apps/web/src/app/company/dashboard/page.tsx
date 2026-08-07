import Link from "next/link";
import { BarChart3, ClipboardList, DollarSign, Users } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AssignedTrainings } from "@/components/company/assigned-trainings";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent } from "@/components/ui/card";
import { getCompanyDashboardSummary } from "@/lib/adapters/companyAdapter";

const links = [
  { title: "Assigned Trainings", href: "/company/trainings" },
  { title: "Employees", href: "/company/employees" },
  { title: "Reports", href: "/company/reports" },
  { title: "Usage & Cost", href: "/company/usage" },
];

export const dynamic = "force-dynamic";

export default async function CompanyDashboardPage() {
  const summary = await getCompanyDashboardSummary("company-demo");

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["company"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Company workspace</p>
            <h1 className="mt-2 text-3xl font-semibold">HR training dashboard</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Customer-side view for assigned trainings, employee enrollments, company reports, and usage.</p>
          </section>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric title="Assigned trainings" value={`${summary.assignedTrainingCount}`} detail="From platform" icon={ClipboardList} />
            <Metric title="Completion" value={`${summary.completionRate}%`} detail="Current cohort" icon={BarChart3} />
            <Metric title="Skill impact" value={`+${summary.averageSkillLift}`} detail="Average lift" icon={BarChart3} />
            <Metric title="Usage" value="$148" detail="Mock monthly cost" icon={DollarSign} />
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {links.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-teal-300 hover:bg-teal-50">
                <p className="font-semibold">{item.title}</p>
              </Link>
            ))}
          </div>
          <AssignedTrainings />
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}

function Metric({ title, value, detail, icon: Icon }: { title: string; value: string; detail: string; icon: typeof Users }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium text-slate-600">{title}</p>
          <Icon className="h-5 w-5 text-teal-700" />
        </div>
        <p className="mt-3 text-3xl font-semibold">{value}</p>
        <p className="mt-1 text-sm text-slate-500">{detail}</p>
      </CardContent>
    </Card>
  );
}
