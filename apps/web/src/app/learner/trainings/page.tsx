"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PlayCircle } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnerTrainings } from "@/lib/adapters/learnerAdapter";

type LearnerTrainings = Awaited<ReturnType<typeof getLearnerTrainings>>;

export default function LearnerTrainingsPage() {
  const [assignedTrainings, setAssignedTrainings] = useState<LearnerTrainings>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getLearnerTrainings()
      .then((data) => {
        if (!cancelled) {
          setAssignedTrainings(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load assigned trainings.");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">My trainings</p>
            <h1 className="mt-2 text-3xl font-semibold">Assigned training list</h1>
            <p className="mt-2 text-slate-600">Learner-only view of trainings assigned by your company.</p>
          </section>

          {loading ? (
            <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500">
              Loading assigned trainings...
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          ) : assignedTrainings.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500">
              No trainings currently assigned.
            </div>
          ) : (
            <div className="grid gap-4">
              {assignedTrainings.map((training) => (
                <Card key={training.id} className="rounded-lg border-slate-200">
                  <CardHeader>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <CardTitle>{`Training ${training.moduleId}`}</CardTitle>
                        <p className="mt-1 text-sm leading-6 text-slate-600">
                          Assigned by your company for this learning path.
                        </p>
                      </div>
                      <Badge variant="secondary">{training.status}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Link href="/learner/session/active" className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
                      <PlayCircle className="h-4 w-4" />
                      Start / Continue
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
