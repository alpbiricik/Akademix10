import Link from "next/link";
import { Clock, Layers, MessageCircle } from "lucide-react";
import type { TrainingModule } from "@/lib/state-machine/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export function TrainingCard({ training }: { training: TrainingModule }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader>
        <CardTitle>{training.title}</CardTitle>
        <p className="text-sm leading-6 text-slate-600">{training.description}</p>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
        <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-teal-600" />{training.durationMin} min</div>
        <div className="flex items-center gap-2"><Layers className="h-4 w-4 text-teal-600" />{training.stateIds.length} states</div>
        <div className="flex items-center gap-2"><MessageCircle className="h-4 w-4 text-teal-600" />LiveAvatar Lite</div>
      </CardContent>
      <CardFooter className="justify-between">
        <Badge variant="secondary">{training.status}</Badge>
        <Link href="/learner/trainings" className="inline-flex h-8 shrink-0 items-center justify-center rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
          View
        </Link>
      </CardFooter>
    </Card>
  );
}
