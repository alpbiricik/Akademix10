"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import type { TrainingState } from "@/lib/state-machine/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function AIQuestionBlock({ state }: { state: TrainingState }) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-4">
      <p className="text-sm leading-6 text-slate-700">{state.prompt}</p>
      <Textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Type the learner answer..." className="min-h-32 bg-white" />
      <Button onClick={() => setSubmitted(true)} disabled={!answer.trim()}>
        <Send className="h-4 w-4" />
        Submit answer
      </Button>
      {submitted ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-700">
          <p className="font-semibold text-slate-950">AI feedback</p>
          <p className="mt-2">Mock feedback generated from the learner answer. The canonical session runner stores feedback on the TrainingSession object.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {state.skillTags.map((skill) => (
              <span key={skill} className="rounded-md bg-white px-2 py-1 text-xs font-medium text-slate-700 ring-1 ring-amber-200">
                {skill}: +2
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
