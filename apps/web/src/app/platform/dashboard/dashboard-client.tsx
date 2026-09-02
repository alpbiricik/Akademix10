"use client";

import Link from "next/link";
import { Building2, DollarSign, LibraryBig, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Card, CardContent } from "@/components/ui/card";
import { getPlatformDashboardSummary } from "@/lib/adapters/platformAdapter";

type PlatformDashboardSummary = Awaited<ReturnType<typeof getPlatformDashboardSummary>>;

export function PlatformDashboardClient({ links }: { links: Array<{ title: string; href: string }> }) {
  const [summary, setSummary] = useState<PlatformDashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getPlatformDashboardSummary()
      .then((value) => {
        if (!cancelled) setSummary(value);
      })
      .catch(() => {
        if (!cancelled) setError("Dashboard data could not be loaded.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ProtectedRoute allowedRoles={["platform"]}>
      <div className="space-y-6">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Platform workspace</p>
          <h1 className="mt-2 text-3xl font-semibold">AkademX10 operator dashboard</h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            Internal SaaS view for templates, customer companies, training assignments, and cost-aware AI session operations.
          </p>
        </section>

        {error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric title="Templates" value={summary ? `${summary.templateCount}` : "..."} detail="Reusable training products" icon={LibraryBig} />
          <Metric title="Companies" value={summary ? `${summary.companyCount}` : "..."} detail="Customer tenants" icon={Building2} />
          <Metric title="Assignments" value={summary ? `${summary.activeAssignmentCount}` : "..."} detail="Active customer rollouts" icon={Send} />
          <Metric title="Avg budget" value={summary ? `$${summary.safeBudgetUsd.toFixed(2)}` : "..."} detail="Safe session budget" icon={DollarSign} />
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
