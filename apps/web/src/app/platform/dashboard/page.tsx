import Link from "next/link";
import { Building2, DollarSign, LibraryBig, Send } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAllCompanies } from "@/lib/repositories/companyRepository";
import { getAllTrainingTemplates } from "@/lib/repositories/trainingRepository";

const links = [
  { title: "Training Templates", href: "/platform/templates" },
  { title: "Companies", href: "/platform/companies" },
  { title: "Assignments", href: "/platform/assignments" },
  { title: "Usage & Cost", href: "/platform/usage" },
];

export default function PlatformDashboardPage() {
  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Platform workspace</p>
            <h1 className="mt-2 text-3xl font-semibold">AkademX10 operator dashboard</h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Internal SaaS view for templates, customer companies, training assignments, and cost-aware AI session operations.
            </p>
          </section>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric title="Templates" value={`${getAllTrainingTemplates().length}`} detail="Reusable training products" icon={LibraryBig} />
            <Metric title="Companies" value={`${getAllCompanies().length}`} detail="Mock customer tenants" icon={Building2} />
            <Metric title="Assignments" value="7" detail="Active customer rollouts" icon={Send} />
            <Metric title="Avg budget" value="$1.25" detail="Safe session budget" icon={DollarSign} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {links.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300 hover:bg-teal-50">
                <p className="font-semibold">{item.title}</p>
                <p className="mt-2 text-sm text-slate-600">Open {item.title.toLowerCase()}.</p>
              </Link>
            ))}
          </div>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}

function Metric({ title, value, detail, icon: Icon }: { title: string; value: string; detail: string; icon: typeof LibraryBig }) {
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
