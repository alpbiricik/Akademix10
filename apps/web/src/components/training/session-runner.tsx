"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowLeft, ArrowRight, BadgeDollarSign, Bot, CheckCircle2, Circle, CircleDot, FileText, MessageSquareText, Mic, PlayCircle, RotateCcw, Sparkles, Square } from "lucide-react";
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
import { formatUsd, getStateTypeLabel, getStateTypeTone, isAvatarState, isInteractiveState, sortStatesByOrder } from "@/lib/state-machine/utils";
import { completeCurrentState, finalizeSession, getSessionBundle, moveToNextState, moveToPreviousState, resetDemoSession, startVoiceOpening, submitConversationTurn, submitSessionAnswer } from "@/lib/adapters/sessionAdapter";
import { API_BASE_URL, DATA_SOURCE_MODE } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import type { MockAIFeedback, TrainingModule, TrainingSession, TrainingState, TrainingTemplate } from "@/lib/state-machine/types";

type VoiceStatus = "idle" | "listening" | "processing" | "speaking" | "complete" | "error";

export function SessionRunner({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [states, setStates] = useState<TrainingState[]>([]);
  const [training, setTraining] = useState<TrainingModule | null>(null);
  const [template, setTemplate] = useState<TrainingTemplate | null>(null);
  const [draft, setDraft] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const [voicePartial, setVoicePartial] = useState("");
  const [voiceFinal, setVoiceFinal] = useState("");
  const [voiceAssistantText, setVoiceAssistantText] = useState("");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const submitInFlightRef = useRef(false);
  const finalizeInFlightRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const voiceStartInFlightRef = useRef(false);
  const voiceOpeningKeyRef = useRef<string | null>(null);
  const voiceAudioRef = useRef<HTMLAudioElement | null>(null);

  const cleanupVoiceTurn = useCallback(() => {
    audioProcessorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    void audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    audioProcessorRef.current = null;
    audioSourceRef.current = null;
    audioContextRef.current = null;
    mediaStreamRef.current = null;
    if (voiceSocketRef.current?.readyState === WebSocket.OPEN) voiceSocketRef.current.send("cancel");
    voiceSocketRef.current?.close();
    voiceSocketRef.current = null;
    voiceAudioRef.current?.pause();
    voiceAudioRef.current = null;
    voiceStartInFlightRef.current = false;
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      let bundle = await getSessionBundle(sessionId);
      if (!bundle) {
        const reset = await resetDemoSession();
        bundle = await getSessionBundle(reset.id);
      }
      if (!bundle) return;
      const { session: loaded, states: loadedStates, module: loadedTraining, template: loadedTemplate } = bundle;
      if (!active) return;
      setSession(isTrainingSession(loaded) ? { ...loaded, usage: calculateMockUsage(loaded, loadedStates as TrainingState[]) } : null);
      setStates(loadedStates as TrainingState[]);
      setTraining(loadedTraining);
      setTemplate(loadedTemplate);
      if (DATA_SOURCE_MODE === "api") {
        setDrafts(readSessionDrafts(loaded.id));
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => {
    return () => {
      cleanupVoiceTurn();
    };
  }, [cleanupVoiceTurn]);

  const sortedStates = useMemo(() => sortStatesByOrder(states), [states]);
  const currentState = session ? getCurrentState(session, sortedStates) : null;
  const progress = session ? getSessionProgress(session, sortedStates) : { completed: 0, total: sortedStates.length, percent: 0 };
  const currentFeedback = session && currentState ? session.feedback.find((item) => item.stateId === currentState.id) : undefined;
  const currentStateId = currentState?.id;

  const applySession = useCallback((next: TrainingSession) => {
    const withUsage = { ...next, usage: calculateMockUsage(next, sortedStates) };
    setSession(withUsage);
  }, [sortedStates]);

  useEffect(() => {
    if (!session || !currentStateId) return;
    queueMicrotask(() => {
      setDraft(DATA_SOURCE_MODE === "api" ? drafts[currentStateId] ?? "" : session.answers.find((item) => item.stateId === currentStateId)?.answerText ?? "");
      setSubmitError(null);
    });
  }, [currentStateId, drafts, session]);

  useEffect(() => {
    cleanupVoiceTurn();
    voiceOpeningKeyRef.current = null;
    queueMicrotask(() => {
      setVoiceStatus("idle");
      setVoicePartial("");
      setVoiceFinal("");
      setVoiceAssistantText("");
      setVoiceError(null);
    });
  }, [cleanupVoiceTurn, currentStateId]);

  useEffect(() => {
    if (!session || !currentState || !isAvatarState(currentState)) return;
    if (session.completedStateIds.includes(currentState.id)) return;
    const openingKey = `${session.id}:${currentState.id}`;
    if (voiceOpeningKeyRef.current === openingKey) return;
    voiceOpeningKeyRef.current = openingKey;
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setVoiceStatus("processing");
      setVoiceError(null);
      setVoicePartial("");
      setVoiceFinal("");
      setVoiceAssistantText("");
      startVoiceOpening(session.id, currentState.id)
        .then(async (result) => {
          if (cancelled) return;
          setVoiceAssistantText(result.assistantText);
          setVoiceStatus("speaking");
          await playVoiceAudio(result.tts?.audioPayloadBase64, result.tts?.contentType);
          if (cancelled) return;
          setVoiceStatus(result.conversationComplete ? "complete" : "idle");
          if (result.conversationComplete) {
            applySession({ ...session, completedStateIds: Array.from(new Set([...session.completedStateIds, currentState.id])) });
          }
        })
        .catch(() => {
          if (!cancelled) {
            setVoiceError("Voice opening failed. Type your response instead.");
            setVoiceStatus("error");
          }
        });
    });
    return () => {
      cancelled = true;
    };
  }, [applySession, currentState, session]);

  async function handleSubmit() {
    if (!session || !currentState || !draft.trim() || submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      if (DATA_SOURCE_MODE === "api") {
        const nextDrafts = { ...drafts, [currentState.id]: draft.trim() };
        setDrafts(nextDrafts);
        writeSessionDrafts(session.id, nextDrafts);
        const updated = await completeCurrentState(session.id);
        if (isTrainingSession(updated)) applySession(updated);
        return;
      }
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
    const bundle = await getSessionBundle(reset.id);
    const resetStates = bundle?.states ?? [];
    setStates(resetStates as TrainingState[]);
    setSession({ ...reset, usage: calculateMockUsage(reset, resetStates as TrainingState[]) });
    setTraining(bundle?.module ?? null);
    setTemplate(bundle?.template ?? null);
    setDraft("");
    setDrafts({});
    clearSessionDrafts(reset.id);
    setSubmitError(null);
  }

  async function handleFinalize() {
    if (!session || finalizeInFlightRef.current) return;
    finalizeInFlightRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const answers = sortedStates
        .filter((state) => isInteractiveState(state))
        .map((state) => ({ stateId: state.id, answerText: drafts[state.id]?.trim() ?? "" }))
        .filter((answer) => answer.answerText);
      const updated = await finalizeSession(session.id, {
        idempotencyKey: getFinalizeKey(session.id),
        contractVersion: "2.0",
        answers,
        sessionVersion: session.updatedAt,
      });
      if (isTrainingSession(updated)) applySession(updated);
      clearSessionDrafts(session.id);
      setDrafts({});
    } catch (error) {
      setSubmitError(getSubmitErrorMessage(error));
    } finally {
      finalizeInFlightRef.current = false;
      setIsSubmitting(false);
    }
  }

  function websocketUrl(path: string) {
    const base = API_BASE_URL.replace(/^http/, "ws");
    return `${base}${path}`;
  }

  function stopAudioCapture() {
    audioProcessorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    void audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    audioProcessorRef.current = null;
    audioSourceRef.current = null;
    audioContextRef.current = null;
    mediaStreamRef.current = null;
  }

  function playVoiceAudio(audioPayloadBase64?: string | null, contentType?: string | null) {
    if (!audioPayloadBase64) return Promise.resolve();
    try {
      const bytes = Uint8Array.from(atob(audioPayloadBase64), (char) => char.charCodeAt(0));
      const blob = new Blob([bytes], { type: contentType || "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      voiceAudioRef.current = audio;
      return new Promise<void>((resolve) => {
        const finish = () => {
          URL.revokeObjectURL(url);
          if (voiceAudioRef.current === audio) voiceAudioRef.current = null;
          resolve();
        };
        audio.onended = finish;
        audio.onerror = finish;
        void audio.play().catch(finish);
      });
    } catch {
      return Promise.resolve();
    }
  }

  async function handleStartVoiceTurn() {
    if (!session || !currentState || voiceStartInFlightRef.current || voiceStatus !== "idle") return;
    if (session.completedStateIds.includes(currentState.id)) {
      setVoiceError("This conversation state is already complete.");
      setVoiceStatus("error");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === "undefined") {
      setVoiceError("Microphone capture is not available in this browser.");
      setVoiceStatus("error");
      return;
    }
    voiceStartInFlightRef.current = true;
    setVoiceError(null);
    setVoicePartial("");
    setVoiceFinal("");
    setVoiceAssistantText("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const socket = new WebSocket(websocketUrl(`/api/learner/sessions/${session.id}/voice/stt`));
      voiceSocketRef.current = socket;
      socket.binaryType = "arraybuffer";
      socket.onopen = () => {
        socket.send(JSON.stringify({ stateId: currentState.id, mockRole: "learner", accessToken: readSupabaseAccessToken() }));
        const context = new AudioContext();
        const source = context.createMediaStreamSource(stream);
        const processor = context.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (audioEvent) => {
          if (socket.readyState !== WebSocket.OPEN) return;
          const input = audioEvent.inputBuffer.getChannelData(0);
          socket.send(floatToPcm16(input, context.sampleRate, 16000));
        };
        source.connect(processor);
        processor.connect(context.destination);
        audioContextRef.current = context;
        audioSourceRef.current = source;
        audioProcessorRef.current = processor;
        setVoiceStatus("listening");
        voiceStartInFlightRef.current = false;
      };
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data as string) as { type?: string; transcript?: string; result?: { assistantText?: string; conversationComplete?: boolean; tts?: { audioPayloadBase64?: string | null; contentType?: string | null } } ; code?: string };
        if (payload.type === "partial_transcript") setVoicePartial(payload.transcript ?? "");
        if (payload.type === "final_transcript" || payload.type === "committed_transcript") {
          setVoiceFinal(payload.transcript ?? "");
          setVoiceStatus("processing");
          stopAudioCapture();
        }
        if (payload.type === "voice_turn_result" && payload.result) {
          setVoiceAssistantText(payload.result.assistantText ?? "");
          setVoiceStatus("speaking");
          void playVoiceAudio(payload.result.tts?.audioPayloadBase64, payload.result.tts?.contentType).then(() => {
            setVoiceStatus(payload.result?.conversationComplete ? "complete" : "idle");
          });
          if (payload.result.conversationComplete && session && currentState) {
            applySession({ ...session, completedStateIds: Array.from(new Set([...session.completedStateIds, currentState.id])) });
          }
        }
        if (payload.type === "error") {
          setVoiceError(voiceErrorMessage(payload.code));
          setVoiceStatus("error");
          cleanupVoiceTurn();
        }
      };
      socket.onerror = () => {
        setVoiceError("Voice streaming connection failed. Type your response instead.");
        setVoiceStatus("error");
        cleanupVoiceTurn();
      };
      socket.onclose = () => {
        voiceStartInFlightRef.current = false;
      };
    } catch (error) {
      cleanupVoiceTurn();
      setVoiceError(error instanceof DOMException && error.name === "NotAllowedError" ? "Microphone permission was denied." : "Microphone could not be started.");
      setVoiceStatus("error");
    }
  }

  function handleStopVoiceTurn() {
    if (voiceStatus === "listening") {
      stopAudioCapture();
      if (voiceSocketRef.current?.readyState === WebSocket.OPEN) voiceSocketRef.current.send("stop");
      setVoiceStatus("processing");
    } else {
      cleanupVoiceTurn();
      setVoiceStatus("idle");
    }
  }

  async function handleTypedConversationTurn(text: string) {
    if (!session || !currentState || !text.trim() || submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setVoiceStatus("processing");
    setVoiceError(null);
    try {
      const result = await submitConversationTurn(session.id, { stateId: currentState.id, learnerText: text.trim() });
      setVoiceFinal(text.trim());
      setVoiceAssistantText(result.assistantText);
      if (result.conversationComplete) applySession({ ...session, completedStateIds: Array.from(new Set([...session.completedStateIds, currentState.id])) });
      setVoiceStatus(result.conversationComplete ? "complete" : "idle");
    } catch {
      setVoiceError("Conversation turn failed. Try typing again.");
      setVoiceStatus("error");
    } finally {
      submitInFlightRef.current = false;
    }
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
                  isBatchMode={DATA_SOURCE_MODE === "api"}
                  canMoveNext={canMoveNext(session, sortedStates)}
                  onChange={(value) => {
                    setDraft(value);
                    if (submitError) setSubmitError(null);
                  }}
                  onSubmit={handleSubmit}
                  onMoveNext={handleMoveNext}
                />
              ) : null}
              {isAvatarState(currentState) ? (
                <VoicePocBox
                  status={voiceStatus}
                  partial={voicePartial}
                  finalTranscript={voiceFinal}
                  assistantText={voiceAssistantText}
                  error={voiceError}
                  disabled={session.completedStateIds.includes(currentState.id) || voiceStatus === "complete"}
                  onStart={handleStartVoiceTurn}
                  onStop={handleStopVoiceTurn}
                  onTypedSubmit={handleTypedConversationTurn}
                />
              ) : null}
              <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-5">
                <Button variant="outline" onClick={handleMovePrevious} disabled={!canMovePrevious(session, sortedStates)}><ArrowLeft className="h-4 w-4" />Previous State</Button>
                <Button variant="secondary" onClick={handleComplete} disabled={session.completedStateIds.includes(currentState.id)}><CheckCircle2 className="h-4 w-4" />Complete State</Button>
                <Button onClick={handleMoveNext} disabled={!canMoveNext(session, sortedStates)}>Next State<ArrowRight className="h-4 w-4" /></Button>
                {DATA_SOURCE_MODE === "api" && currentState.type === "final" ? (
                  <Button type="button" onClick={handleFinalize} disabled={isSubmitting}>
                    <Sparkles className="h-4 w-4" />
                    {isSubmitting ? "Finalizing..." : "Finalize"}
                  </Button>
                ) : null}
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

function draftStorageKey(sessionId: string) {
  return `akademx10.sessionDraft.${sessionId}`;
}

function readSessionDrafts(sessionId: string): Record<string, string> {
  try {
    const raw = window.sessionStorage.getItem(draftStorageKey(sessionId));
    return raw ? JSON.parse(raw) as Record<string, string> : {};
  } catch {
    return {};
  }
}

function writeSessionDrafts(sessionId: string, drafts: Record<string, string>) {
  window.sessionStorage.setItem(draftStorageKey(sessionId), JSON.stringify(drafts));
}

function clearSessionDrafts(sessionId: string) {
  window.sessionStorage.removeItem(draftStorageKey(sessionId));
}

function getFinalizeKey(sessionId: string) {
  const key = `akademx10.finalizeKey.${sessionId}`;
  const existing = window.sessionStorage.getItem(key);
  if (existing) return existing;
  const next = `${sessionId}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  window.sessionStorage.setItem(key, next);
  return next;
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
  isBatchMode,
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
  isBatchMode: boolean;
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
          {isSubmitting ? "Saving..." : isBatchMode ? "Save answer" : "Submit for AI Feedback"}
        </Button>
      </div>
      {feedback ? <FeedbackCard feedback={feedback} /> : null}
    </div>
  );
}

function VoicePocBox({
  status,
  partial,
  finalTranscript,
  assistantText,
  error,
  disabled,
  onStart,
  onStop,
  onTypedSubmit,
}: {
  status: VoiceStatus;
  partial: string;
  finalTranscript: string;
  assistantText: string;
  error: string | null;
  disabled: boolean;
  onStart: () => void;
  onStop: () => void;
  onTypedSubmit: (text: string) => void;
}) {
  const [typed, setTyped] = useState("");
  const busy = status === "listening" || status === "processing" || status === "speaking";
  const statusText = status === "listening" ? "Listening" : status === "processing" ? "Processing" : status === "speaking" ? "Speaking" : disabled || status === "complete" ? "Conversation complete" : "Ready";
  return (
    <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-teal-950">Voice turn</p>
          <p className="text-sm text-teal-800">{statusText}</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" onClick={onStart} disabled={busy || disabled}>
            <Mic className="h-4 w-4" />
            Start
          </Button>
          <Button type="button" variant="outline" onClick={onStop} disabled={!busy}>
            <Square className="h-4 w-4" />
            Stop
          </Button>
        </div>
      </div>
      {partial ? <p className="mt-3 rounded-md bg-white px-3 py-2 text-sm text-slate-600">Partial: {partial}</p> : null}
      {finalTranscript ? <p className="mt-3 rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-900">Final: {finalTranscript}</p> : null}
      {assistantText ? <p className="mt-3 rounded-md border border-teal-200 bg-white px-3 py-2 text-sm leading-6 text-teal-950">{assistantText}</p> : null}
      {error ? (
        <div role="alert" className="mt-3 flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      ) : null}
      <div className="mt-4 border-t border-teal-200 pt-4">
        <Textarea value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="Type the same turn if microphone or STT is unavailable..." className="min-h-24 bg-white" />
        <div className="mt-2 flex justify-end">
          <Button
            type="button"
            variant="secondary"
            disabled={!typed.trim() || busy || disabled}
            onClick={() => {
              onTypedSubmit(typed);
              setTyped("");
            }}
          >
            <Sparkles className="h-4 w-4" />
            Send typed turn
          </Button>
        </div>
      </div>
    </div>
  );
}

function readSupabaseAccessToken() {
  try {
    const raw = window.localStorage.getItem("akademx10.supabaseSession");
    return raw ? (JSON.parse(raw) as { accessToken?: string }).accessToken ?? null : null;
  } catch {
    return null;
  }
}

function voiceErrorMessage(code?: string) {
  if (code === "stt_provider_not_configured") return "Speech recognition is not configured. Type your response instead.";
  if (code === "empty_transcript") return "No clear speech was detected. Try again or type your response.";
  if (code === "session_not_found" || code === "state_not_found") return "This voice turn is no longer available.";
  return "Voice turn failed. Type your response instead.";
}

function floatToPcm16(input: Float32Array, sourceRate: number, targetRate: number) {
  const ratio = sourceRate / targetRate;
  const length = Math.floor(input.length / ratio);
  const output = new Int16Array(length);
  for (let index = 0; index < length; index += 1) {
    const sample = input[Math.floor(index * ratio)] ?? 0;
    const clamped = Math.max(-1, Math.min(1, sample));
    output[index] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return output.buffer;
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
