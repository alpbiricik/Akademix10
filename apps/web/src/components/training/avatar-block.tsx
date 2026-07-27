import { Bot } from "lucide-react";
import type { TrainingState } from "@/lib/state-machine/types";

export function AvatarBlock({ state }: { state: TrainingState }) {
  return (
    <div className="rounded-lg border border-teal-200 bg-teal-50 p-5">
      <div className="flex items-start gap-4">
        <div className="rounded-md bg-teal-600 p-3 text-white">
          <Bot className="h-6 w-6" />
        </div>
        <div>
          <p className="font-semibold text-slate-950">AI coach</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{state.prompt}</p>
          <p className="mt-3 text-xs font-medium uppercase tracking-wide text-teal-700">LiveAvatar Lite coaching moment</p>
        </div>
      </div>
    </div>
  );
}
