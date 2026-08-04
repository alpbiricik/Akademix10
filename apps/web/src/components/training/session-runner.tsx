"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, BadgeDollarSign, Bot, CheckCircle2, Circle, CircleDot, FileText, MessageSquareText, PlayCircle, RotateCcw, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  calculateMockUsage,
  canMoveNext,
  canMovePrevious,
  getCurrentState,
  getSessionProgress,
} from "@/lib/state-machine/engine";
import { formatUsd, getStateTypeLabel, getStateTypeTone, isInteractiveState, sortStatesByOrder } from "@/lib/state-machine/utils";
import { getLearnerTrainings } from "@/lib/adapters/learnerAdapter";
import { getPlatformTemplates } from "@/lib/adapters/platformAdapter";
import { completeCurrentState, getSession, getSessionStates, moveToNextState, moveToPreviousState, resetDemoSession, submitSessionAnswer } from "@/lib/adapters/sessionAdapter";
import { ApiError } from "@/lib/api/errors";
import type { MockAIFeedback, TrainingModule, TrainingSession, TrainingState, TrainingTemplate } from "@/lib/state-machine/types";

export function SessionRunner({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [states, setStates] = useState<TrainingState[]>([]);
  const [trainings, setTrainings] = useState<TrainingModule[]>([]);
  const [templates, setTemplates] = useState<TrainingTemplate[]>([]);
  const [draft, setDraft] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitInFlightRef = useRef(false);

  useEffect(() => {
    let active = true;
    async function load() {
      const loaded = (await getSession(sessionId)) ?? await resetDemoSession();
      const loadedStates = await getSessionStates(loaded.id);
      const [loadedTrainings, loadedTemplates] = await Promise.all([getLearnerTrainings(), getPlatformTemplates()]);
      if (!active) return;
      setSession(isTrainingSession(loaded) ? { ...loaded, usage: calculateMockUsage(loaded, loadedStates as TrainingState[]) } : null);
      setStates(loadedStates as TrainingState[]);
      setTrainings(loadedTrainings.filter((item): item is TrainingModule => "stateIds" in item));
      setTemplates(loadedTemplates as TrainingTemplate[]);
    }
    load();
    return () => {
      active = false;
    };
  }, [sessionId]);

  const sortedStates = useMemo(() => sortStatesByOrder(states), [states]);
  const currentState = session ? getCurrentState(session, sortedStates) : null;
  const progress = session ? getSessionProgress(session, sortedStates) : { completed: 0, total: sortedStates.length, percent: 0 };
  const training = session ? trainings.find((item) => item.id === session.moduleId) : null;
  const template = session ? templates.find((item) => item.id === session.templateId) : null;
  const currentFeedback = session && currentState ? session.feedback.find((item) => item.stateId === currentState.id) : undefined;
  const currentStateId = currentState?.id;

  useEffect(() => {
    if (!session || !currentStateId) return;
    queueMicrotask(() => {
      setDraft(session.answers.find((item) => item.stateId === currentStateId)?.answerText ?? "");
      setSubmitError(null);
    });
  }, [currentStateId, session]);

  function applySession(next: TrainingSession) {
    const withUsage = { ...next, usage: calculateMockUsage(next, sortedStates) };
    setSession(withUsage);
  }

  async function handleSubmit() {
    if (!session || !currentState || !draft.trim() || submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const updated = await submitSessionAnswer(session.id, { stateId: currentState.id, answerText: draft.trim() });
      if (isTrainingSession(updated)) applySession(updated);
    } catch (error) {
      setSubmitError(getSubmitErrorMessage(error));
    } finally {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
    }
  }

  async function handleComplete() {
    if (!session) return;
    const updated = await completeCurrentState(session.id);
    if (isTrainingSession(updated)) applySession(updated);
  }

  async function handleMoveNext() {
    if (!session) return;
    const updated = await moveToNextState(session.id);
    if (isTrainingSession(updated)) applySession(updated);
    setSubmitError(null);
  }

  async function handleMovePrevious() {
    if (!session) return;
    const updated = await moveToPreviousState(session.id);
    if (isTrainingSession(updated)) applySession(updated);
    setSubmitError(null);
  }

  async function handleReset() {
    const reset = await resetDemoSession();
    const resetStates = await getSessionStates(reset.id);
    setStates(resetStates as TrainingState[]);
    setSession({ ...reset, usage: calculateMockUsage(reset, resetStates as TrainingState[]) });
    setDraft("");
    setSubmitError(null);
  }

  if (!session || !currentState) {
    return <Card className="rounded-lg border-slate-200"><CardContent className="p-6 text-sm text-slate-600">Loading session...</CardContent></Card>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">{template?.category ?? "Core MVP Engine"}</p>
            <h1 className="mt-2 text-3xl font-semibold">{training?.title ?? "Demo training session"}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{training?.description ?? "Mock AI roleplay session powered by the Phase 2A state machine."}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" />
              Reset Demo Session
            </Button>
            <Link href={`/learner/sessions/${session.id}/report`} className="inline-flex h-9 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white px-2.5 text-sm font-medium text-slate-900 shadow-xs transition hover:bg-slate-100">
              Open Report
            </Link>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="space-y-6">
          <Card className="rounded-lg border-slate-200">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">State {currentState.order} of {sortedStates.length}</p>
                  <CardTitle className="mt-1 text-2xl">{currentState.title}</CardTitle>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={getStateTypeTone(currentState.type)}>{getStateTypeLabel(currentState.type)}</Badge>
                  <Badge variant="outline">{currentState.estimatedMin} min</Badge>
                  {currentState.avatarEnabled ? <Badge className="bg-teal-50 text-teal-800">Avatar-enabled</Badge> : null}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <DynamicStateContent state={currentState} />
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6">
                <p className="font-medium text-slate-950">Rubric</p>
                <p className="mt-1 text-slate-600">{currentState.rubric}</p>
                <div className="mt-3 flex flex-wrap gap-2">{currentState.skillTags.map((tag) => <Badge key={tag} variant="outline">{tag}</Badge>)}</div>
              </div>
              {isInteractiveState(currentState) ? (
                <InteractionBox
                  state={currentState}
                  value={draft}
                  feedback={currentFeedback}
                  error={submitError}
                  isSubmitting={isSubmitting}
                  canMoveNext={canMoveNext(session, sortedStates)}
                  onChange={(value) => {
                    setDraft(value);
                    if (submitError) setSubmitError(null);
                  }}
                  onSubmit={handleSubmit}
                  onMoveNext={handleMoveNext}
                />
              ) : null}
              <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-5">
                <Button variant="outline" onClick={handleMovePrevious} disabled={!canMovePrevious(session, sortedStates)}><ArrowLeft className="h-4 w-4" />Previous State</Button>
                <Button variant="secondary" onClick={handleComplete} disabled={session.completedStateIds.includes(currentState.id)}><CheckCircle2 className="h-4 w-4" />Complete State</Button>
                <Button onClick={handleMoveNext} disabled={!canMoveNext(session, sortedStates)}>Next State<ArrowRight className="h-4 w-4" /></Button>
              </div>
            </CardContent>
          </Card>
        </main>
        <aside className="space-y-4">
          <SessionMetrics session={session} progress={progress} />
          <AvatarCostPanel session={session} />
          <SkillImpactPanel session={session} />
          <StateProgressPanel states={sortedStates} session={session} />
        </aside>
      </div>
    </div>
  );
}

function DynamicStateContent({ state }: { state: TrainingState }) {
  if (state.type === "video") return <StateShell icon={<PlayCircle className="h-10 w-10 text-teal-300" />} title="Training content" text={state.prompt} dark />;
  if (state.type === "avatar") return <StateShell icon={<Bot className="h-6 w-6 text-teal-700" />} title="LiveAvatar Lite active" text={state.prompt} tone="teal" />;
  if (state.type === "roleplay") return <StateShell title="Roleplay scenario" text={state.prompt} tone="amber" />;
  if (state.type === "reflection") return <StateShell title="Reflection prompt" text={state.prompt} tone="violet" />;
  if (state.type === "feedback") return <StateShell icon={<MessageSquareText className="h-5 w-5 text-emerald-700" />} title="Feedback checkpoint" text={state.prompt} tone="emerald" />;
  if (state.type === "final") return <StateShell icon={<FileText className="h-5 w-5 text-teal-300" />} title="Final summary" text={state.prompt} dark />;
  return <StateShell icon={<Sparkles className="h-5 w-5 text-teal-700" />} title="Welcome to the guided session" text={state.prompt} />;
}

function StateShell({ icon, title, text, tone, dark }: { icon?: ReactNode; title: string; text: string; tone?: "teal" | "amber" | "violet" | "emerald"; dark?: boolean }) {
  const toneClass = tone === "teal" ? "border-teal-200 bg-teal-50 text-teal-950" : tone === "amber" ? "border-amber-200 bg-amber-50 text-amber-950" : tone === "violet" ? "border-violet-200 bg-violet-50 text-violet-950" : tone === "emerald" ? "border-emerald-200 bg-emerald-50 text-emerald-950" : "border-slate-200 bg-white text-slate-950";
  return (
    <div className={`rounded-lg border p-5 ${dark ? "border-slate-200 bg-slate-950 text-white" : toneClass}`}>
      <div className="flex items-start gap-3">
        {icon}
        <div>
          <p className="font-semibold">{title}</p>
          <p className={`mt-2 text-sm leading-6 ${dark ? "text-slate-300" : ""}`}>{text}</p>
        </div>
      </div>
    </div>
  );
}

function InteractionBox({
  state,
  value,
  feedback,
  error,
  isSubmitting,
  canMoveNext,
  onChange,
  onSubmit,
  onMoveNext,
}: {
  state: TrainingState;
  value: string;
  feedback?: MockAIFeedback;
  error: string | null;
  isSubmitting: boolean;
  canMoveNext: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onMoveNext: () => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="font-medium text-slate-950">Your response</p>
      <Textarea className="mt-3 min-h-32" value={value} onChange={(event) => onChange(event.target.value)} placeholder={`Type your ${state.type} response here...`} />
      {error ? (
        <div role="alert" className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
          <p>{error}</p>
          {canMoveNext ? (
            <Button type="button" variant="outline" className="mt-3" onClick={onMoveNext}>
              Continue to next state
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      ) : null}
      <div className="mt-3 flex justify-end">
        <Button type="button" onClick={onSubmit} disabled={!value.trim() || isSubmitting}>
          <Sparkles className="h-4 w-4" />
          {isSubmitting ? "Submitting..." : "Submit for AI Feedback"}
        </Button>
      </div>
      {feedback ? <FeedbackCard feedback={feedback} /> : null}
    </div>
  );
}

function getSubmitErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    const code = extractApiErrorCode(error.payload);
    if (error.status === 429 || code === "max_queries_per_state") {
      return "This state has reached its AI feedback limit. Your answer is still here. Continue to the next state or reset the demo session for a clean validation run.";
    }
    if (error.status === 422) return "This answer cannot be scored yet. Check the response and submit again.";
    if (error.status === 0) return "The scoring service could not be reached.";
  }
  return "The answer could not be submitted. Your text was not cleared.";
}

function extractApiErrorCode(payload: unknown) {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (!detail || typeof detail !== "object" || !("code" in detail)) return null;
  const code = (detail as { code?: unknown }).code;
  return typeof code === "string" ? code : null;
}

function FeedbackCard({ feedback }: { feedback: MockAIFeedback }) {
  return (
    <div className="mt-4 rounded-lg border border-teal-200 bg-teal-50 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="font-semibold text-teal-950">AI feedback</p>
        <Badge className="bg-teal-700 text-white">Overall {feedback.overallScore}/100</Badge>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {feedback.dimensions.map((dimension) => <div key={dimension.label} className="rounded-md bg-white px-3 py-2 text-sm"><div className="flex justify-between gap-3"><span className="text-slate-600">{dimension.label}</span><span className="font-semibold text-slate-950">{dimension.score}/100</span></div></div>)}
      </div>
      <p className="mt-4 text-sm leading-6 text-teal-950">{feedback.feedbackText}</p>
      <p className="mt-2 text-sm leading-6 text-teal-900"><span className="font-semibold">Improve:</span> {feedback.improvementSuggestion}</p>
      <p className="mt-2 text-sm leading-6 text-teal-900"><span className="font-semibold">Next action:</span> {feedback.nextAction}</p>
    </div>
  );
}

function StateProgressPanel({ states, session }: { states: TrainingState[]; session: TrainingSession }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>21-state progress</CardTitle></CardHeader>
      <CardContent className="max-h-[640px] space-y-2 overflow-y-auto pr-1">
        {states.map((item) => {
          const isCurrent = item.id === session.currentStateId;
          const isCompleted = session.completedStateIds.includes(item.id);
          const Icon = isCompleted ? CheckCircle2 : isCurrent ? CircleDot : Circle;
          return (
            <div key={item.id} className={`w-full rounded-md border p-3 text-left transition ${isCurrent ? "border-teal-500 bg-teal-50" : isCompleted ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-white"}`}>
              <div className="flex items-start gap-3">
                <Icon className={`mt-0.5 h-4 w-4 ${isCompleted ? "text-emerald-700" : isCurrent ? "text-teal-700" : "text-slate-400"}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{item.order}. {item.title}</p>
                  <div className="mt-2 flex flex-wrap gap-2"><Badge className={getStateTypeTone(item.type)}>{item.type}</Badge>{item.avatarEnabled ? <Bot className="h-4 w-4 shrink-0 text-teal-700" /> : null}</div>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function SessionMetrics({ session, progress }: { session: TrainingSession; progress: { completed: number; total: number; percent: number } }) {
  return <Card className="rounded-lg border-slate-200"><CardHeader><CardTitle>Session metrics</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><MetricRow label="Total session" value={`${session.usage.totalDurationMin} min`} /><MetricRow label="States" value={`${progress.total}`} /><MetricRow label="Completed" value={`${progress.completed} (${progress.percent}%)`} /><MetricRow label="Status" value={session.status} /></CardContent></Card>;
}

function AvatarCostPanel({ session }: { session: TrainingSession }) {
  return <Card className="rounded-lg border-slate-200"><CardHeader><div className="flex items-center gap-2"><BadgeDollarSign className="h-5 w-5 text-teal-700" /><CardTitle>Avatar usage and cost</CardTitle></div></CardHeader><CardContent className="space-y-3 text-sm"><MetricRow label="Mode" value="LiveAvatar Lite" /><MetricRow label="Avatar target" value={`${session.usage.avatarTargetMin} min`} /><MetricRow label="Current avatar used" value={`${session.usage.avatarUsedMin.toFixed(2)} min`} /><MetricRow label="Current avatar opens" value={`${session.usage.avatarOpenCount}`} /><MetricRow label="Buffered avatar target" value={`${session.usage.bufferedAvatarMin} min`} /><MetricRow label="Estimated avatar cost" value={formatUsd(session.usage.estimatedAvatarCostUsd)} /><MetricRow label="Safe budget" value={formatUsd(session.usage.safeBudgetUsd)} /></CardContent></Card>;
}

function SkillImpactPanel({ session }: { session: TrainingSession }) {
  return <Card className="rounded-lg border-slate-200"><CardHeader><CardTitle>Skill impact</CardTitle></CardHeader><CardContent className="space-y-3">{session.skillScores.map((score) => <div key={score.skill} className="space-y-1"><div className="flex justify-between gap-3 text-sm"><span className="font-medium text-slate-700">{score.skill}</span><span className="text-slate-500">{score.score}/100 (+{score.delta})</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${score.score}%` }} /></div></div>)}</CardContent></Card>;
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3 rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">{label}</span><span className="font-medium text-slate-950">{value}</span></div>;
}

function isTrainingSession(value: unknown): value is TrainingSession {
  return Boolean(value && typeof value === "object" && "completedStateIds" in value && "usage" in value);
}
