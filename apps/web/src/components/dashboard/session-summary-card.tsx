import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrainingSession } from "@/lib/state-machine/types";

export function SessionSummaryCard({ session }: { session: TrainingSession }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader>
        <CardTitle>Last session summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-md bg-slate-50 p-3"><p className="text-slate-500">Status</p><p className="font-semibold">{session.status}</p></div>
          <div className="rounded-md bg-slate-50 p-3"><p className="text-slate-500">Completed states</p><p className="font-semibold">{session.completedStateIds.length}</p></div>
          <div className="rounded-md bg-slate-50 p-3"><p className="text-slate-500">Avatar used</p><p className="font-semibold">{session.usage.avatarUsedMin.toFixed(2)} min</p></div>
        </div>
        <Link href={`/learner/session/${session.id}`} className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
          Continue session
          <ArrowRight className="h-4 w-4" />
        </Link>
      </CardContent>
    </Card>
  );
}
