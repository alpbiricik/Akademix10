import type { TrainingState } from "@/lib/state-machine/types";

export function FinalFeedbackBlock({ state }: { state: TrainingState }) {
  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-5">
      <p className="text-sm font-semibold uppercase tracking-wide text-indigo-700">Feedback</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-950">{state.title}</h3>
      <p className="mt-3 text-sm leading-6 text-slate-700">{state.prompt}</p>
    </div>
  );
}
