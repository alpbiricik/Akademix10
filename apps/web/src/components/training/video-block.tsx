import { PlayCircle } from "lucide-react";
import type { TrainingState } from "@/lib/state-machine/types";

export function VideoBlock({ state }: { state: TrainingState }) {
  return (
    <div className="space-y-4">
      <div className="flex aspect-video items-center justify-center rounded-lg border border-slate-200 bg-slate-950 text-white">
        <div className="text-center">
          <PlayCircle className="mx-auto h-12 w-12 text-teal-300" />
          <p className="mt-3 text-sm font-medium">Video lesson</p>
        </div>
      </div>
      <p className="text-sm leading-6 text-slate-600">{state.prompt}</p>
    </div>
  );
}
