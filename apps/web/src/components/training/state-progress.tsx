import type { TrainingState } from "@/lib/state-machine/types";
import { cn } from "@/lib/utils";

export function StateProgress({ states, currentIndex }: { states: TrainingState[]; currentIndex: number }) {
  return (
    <div className="grid grid-cols-7 gap-2 sm:grid-cols-11 lg:grid-cols-21">
      {states.map((state, index) => (
        <div
          key={state.id}
          title={`${state.order}. ${state.title}`}
          className={cn(
            "flex h-8 items-center justify-center rounded-md border text-xs font-semibold",
            index < currentIndex && "border-teal-200 bg-teal-50 text-teal-700",
            index === currentIndex && "border-teal-600 bg-teal-600 text-white",
            index > currentIndex && "border-slate-200 bg-white text-slate-500"
          )}
        >
          {state.order}
        </div>
      ))}
    </div>
  );
}
