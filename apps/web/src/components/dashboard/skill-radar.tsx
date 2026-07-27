import type { SkillScore } from "@/lib/state-machine/types";

export function SkillRadar({ scores }: { scores: SkillScore[] }) {
  return (
    <div className="space-y-3">
      {scores.map((score) => (
        <div key={score.skill}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="font-medium text-slate-700">{score.skill}</span>
            <span className="text-slate-500">{score.score}/100</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-teal-600" style={{ width: `${score.score}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
