import Link from "next/link";
import { PlayCircle } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnerTrainings } from "@/lib/adapters/learnerAdapter";

export default async function LearnerTrainingsPage() {
  const assignedTrainings = await getLearnerTrainings();

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["learner"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">My trainings</p>
            <h1 className="mt-2 text-3xl font-semibold">Assigned training list</h1>
            <p className="mt-2 text-slate-600">Learner-only view of trainings assigned by your company.</p>
          </section>
          <div className="grid gap-4">
            {assignedTrainings.map((training) => (
              <Card key={training.id} className="rounded-lg border-slate-200">
                <CardHeader>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <CardTitle>{"title" in training ? training.title : `Training ${training.moduleId}`}</CardTitle>
                      <p className="mt-1 text-sm leading-6 text-slate-600">
                        {"description" in training ? training.description : "Assigned by your company for this learning path."}
                      </p>
                    </div>
                    <Badge variant="secondary">{"stateIds" in training ? training.stateIds.length : 21} states</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <Link href="/learner/session/demo-session-1" className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
                    <PlayCircle className="h-4 w-4" />
                    Start / Continue
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
