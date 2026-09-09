"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Clock, ListChecks, Mic, PlayCircle, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LiveAvatarView } from "./live-avatar-view";
import {
  canMoveNext,
  canMovePrevious,
  getCurrentState,
  getSessionProgress,
} from "@/lib/state-machine/engine";
import { isAvatarState, isInteractiveState, sortStatesByOrder } from "@/lib/state-machine/utils";
import { cancelVoiceDelivery, recordBrowserVoiceMetric, recoverConversationState, completeCurrentState, finalizeSession, getSessionBundle, getVoiceDelivery, moveToNextState, moveToPreviousState, restartLearnerSession, prepareVoiceOpening, startVoiceOpening, submitConversationTurn } from "@/lib/adapters/sessionAdapter";
import { API_BASE_URL } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import type { TrainingModule, TrainingSession, TrainingState } from "@/lib/state-machine/types";

type VoiceStatus = "idle" | "listening" | "processing" | "speaking" | "complete" | "error";

export function SessionRunner({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [states, setStates] = useState<TrainingState[]>([]);
  const [training, setTraining] = useState<TrainingModule | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const [voiceAssistantText, setVoiceAssistantText] = useState("");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [textTurn, setTextTurn] = useState("");
  const [textPending, setTextPending] = useState(false);
  const textRequestRef = useRef(0);
  const [interactionMode, setInteractionMode] = useState<"text" | "voice" | null>(null);
  const [openingAttempt, setOpeningAttempt] = useState(0);
  const [briefingMode, setBriefingMode] = useState<"text" | "voice">("text");
  const [missingStateIds, setMissingStateIds] = useState<string[]>([]);
  const responseStartedRef = useRef<number | null>(null);
  const playbackFinishRef = useRef<(() => void) | null>(null);
  const [avatarReady, setAvatarReady] = useState(false);
  const finalizeInFlightRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const voiceStartInFlightRef = useRef(false);
  const voiceOpeningKeyRef = useRef<string | null>(null);
  const [preparedOpening, setPreparedOpening] = useState<{ key: string; id: string } | null>(null);
  const preparationRef = useRef<{ key: string; promise: ReturnType<typeof prepareVoiceOpening> } | null>(null);
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
    playbackFinishRef.current?.();
    playbackFinishRef.current = null;
    voiceAudioRef.current = null;
    voiceStartInFlightRef.current = false;
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      queueMicrotask(() => {
        if (!active) return;
        setSession(null);
        setInteractionMode(null);
        textRequestRef.current += 1;
        cleanupVoiceTurn();
      });
      let bundle = await getSessionBundle(sessionId);
      if (!bundle) {
        const restarted = await restartLearnerSession();
        bundle = await getSessionBundle(restarted.id);
      }
      if (!bundle) return;
      const { session: loaded, states: loadedStates, module: loadedTraining } = bundle;
      if (!active) return;
      setSession(isTrainingSession(loaded) ? loaded : null);
      setStates(loadedStates as TrainingState[]);
      setTraining(loadedTraining);
      setDrafts(readSessionDrafts(loaded.id));
      try {
        const savedMode = window.sessionStorage.getItem(`akademx10.sessionMode.${loaded.id}.${loaded.startedAt ?? "new"}`);
        setInteractionMode(savedMode === "text" || savedMode === "voice" ? savedMode : null);
      } catch { setInteractionMode(null); }
    }
    load();
    return () => {
      active = false;
    };
  }, [sessionId, cleanupVoiceTurn]);

  useEffect(() => {
    return () => {
      textRequestRef.current += 1;
      cleanupVoiceTurn();
    };
  }, [cleanupVoiceTurn]);

  const sortedStates = useMemo(() => sortStatesByOrder(states), [states]);
  const currentState = session ? getCurrentState(session, sortedStates) : null;
  const progress = session ? getSessionProgress(session, sortedStates) : { completed: 0, total: sortedStates.length, percent: 0 };
  const currentStateId = currentState?.id;
  const activeSessionId = session?.id;
  const shouldPrepareOpening = Boolean(session && currentState && isAvatarState(currentState) && interactionMode === "voice" && !session.completedStateIds.includes(currentState.id));
  const preparationKey = `${session?.id}:${currentStateId}:${openingAttempt}`;
  const preparedOpeningId = preparedOpening?.key === preparationKey ? preparedOpening.id : undefined;

  useEffect(() => {
    if (!session?.id || !currentStateId || interactionMode !== "voice") return;
    const cancel = () => { void cancelVoiceDelivery(session.id, currentStateId).catch(() => undefined); };
    window.addEventListener("pagehide", cancel);
    return () => {
      window.removeEventListener("pagehide", cancel);
      cancel();
    };
  }, [session?.id, currentStateId, interactionMode]);

  const recordResponse = useCallback((event: "browser_end_to_end" | "browser_playback") => {
    if (!session?.id || !currentStateId || responseStartedRef.current === null) return;
    void recordBrowserVoiceMetric(session.id, currentStateId, event, performance.now() - responseStartedRef.current).catch(() => undefined);
  }, [session, currentStateId]);

  function startTraining() {
    if (!session || interactionMode) return;
    try { window.sessionStorage.setItem(`akademx10.sessionMode.${session.id}.${session.startedAt ?? "new"}`, briefingMode); }
    catch { /* The chosen mode remains valid for this mounted session. */ }
    setInteractionMode(briefingMode);
  }

  const applySession = useCallback((next: TrainingSession) => {
    setSession(next);
  }, []);

  useEffect(() => {
    if (!session || !currentStateId) return;
    queueMicrotask(() => {
      setSubmitError(null);
    });
  }, [currentStateId, drafts, session]);

  const previousStateIdRef = useRef<string | null | undefined>(null);

  useEffect(() => {
    if (previousStateIdRef.current !== currentStateId) {
      previousStateIdRef.current = currentStateId;
      textRequestRef.current += 1;
      cleanupVoiceTurn();
      voiceOpeningKeyRef.current = null;
      queueMicrotask(() => {
        setPreparedOpening(null);
        preparationRef.current = null;
        setTextTurn("");
        setTextPending(false);
        setVoiceStatus("idle");
        setVoiceAssistantText("");
        setVoiceError(null);
        setAvatarReady(false);
      });
    }
  }, [cleanupVoiceTurn, currentStateId]);

  const playVoiceAudio = useCallback((audioPayloadBase64?: string | null, contentType?: string | null) => {
    if (!audioPayloadBase64) return Promise.resolve();
    try {
      const bytes = Uint8Array.from(atob(audioPayloadBase64), (char) => char.charCodeAt(0));
      const blob = new Blob([bytes], { type: contentType || "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      voiceAudioRef.current = audio;
      return new Promise<void>((resolve) => {
        const finish = () => {
          playbackFinishRef.current = null;
          URL.revokeObjectURL(url);
          if (voiceAudioRef.current === audio) voiceAudioRef.current = null;
          resolve();
        };
        playbackFinishRef.current = finish;
        audio.onplaying = () => recordResponse("browser_playback");
        audio.onended = finish;
        audio.onerror = finish;
        void audio.play().catch(finish);
      });
    } catch {
      return Promise.resolve();
    }
  }, [recordResponse]);

  const waitForAvatarSpeech = useCallback(async (text?: string | null, deliverySessionId?: string, deliveryId?: string | null) => {
    const characterCount = Math.max((text ?? "").trim().length, 40);
    const estimatedMs = Math.min(Math.max(Math.round((characterCount / 13) * 1000) + 700, 2200), 18000);
    const generation = textRequestRef.current;
    const deadline = Date.now() + estimatedMs;
    const deliveryDeadline = Date.now() + 90000;
    const pause = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));
    if (deliverySessionId && deliveryId) {
      while (Date.now() < deliveryDeadline && generation === textRequestRef.current) {
        const remaining = Math.max(0, deliveryDeadline - Date.now());
        const delivery = await Promise.race([
          getVoiceDelivery(deliverySessionId, deliveryId).catch(() => null),
          pause(Math.min(5000, remaining)).then(() => null),
        ]);
        if (generation !== textRequestRef.current) return;
        if (!delivery) {
          setVoiceError("Ses aktarımı doğrulanamadı. Yanıt metnini okuyarak devam edebilirsin.");
          break;
        }
        if (delivery.status === "fallback") {
          setVoiceError("Avatar sesi aktarilamadi. Yanit ses olarak oynatiliyor; metni de okuyabilirsin.");
          await playVoiceAudio(delivery.audioPayloadBase64, delivery.contentType);
          return;
        }
        if (delivery.status === "expired" || delivery.status === "cancelled" || delivery.status === "failed" || delivery.status === "text_only") {
          setVoiceError(delivery.errorCode ? voiceErrorMessage(delivery.errorCode) : "Ses aktarim durumu alinamadi. Yanit metnini okuyarak devam edebilirsin.");
          break;
        }
        if (delivery.status === "completed") break;
        await pause(Math.min(750, Math.max(0, deliveryDeadline - Date.now())));
      }
    }
    if (generation === textRequestRef.current) await pause(Math.max(0, deadline - Date.now()));
  }, [playVoiceAudio]);

  useEffect(() => {
    if (!shouldPrepareOpening || !activeSessionId || !currentStateId) return;
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setVoiceStatus("processing");
      setVoiceError(null);
      setAvatarReady(false);
      if (preparationRef.current?.key !== preparationKey) {
        preparationRef.current = { key: preparationKey, promise: prepareVoiceOpening(activeSessionId, currentStateId) };
      }
      void preparationRef.current.promise.then((result) => {
        if (!active) return;
        setVoiceAssistantText(result.assistantText);
        if (!result.preparedOpeningId) {
          setPreparedOpening(null);
          setVoiceStatus("error");
          setVoiceError(voiceErrorMessage(result.errorCode ?? undefined));
          return;
        }
        setPreparedOpening({ key: preparationKey, id: result.preparedOpeningId });
      }).catch((error) => {
        if (!active) return;
        setPreparedOpening(null);
        setVoiceStatus("error");
        setVoiceError(error instanceof ApiError ? voiceErrorMessage(extractApiErrorCode(error.payload) ?? undefined) : "Acilis hazirlanamadi. Tekrar dene veya yazarak devam et.");
      });
    });
    return () => { active = false; };
  }, [activeSessionId, currentStateId, shouldPrepareOpening, preparationKey]);

  useEffect(() => {
    if (!session || !currentState || !isAvatarState(currentState)) return;
    if (!interactionMode || (interactionMode === "voice" && (!avatarReady || !preparedOpeningId))) return;
    if (session.completedStateIds.includes(currentState.id)) return;
    const openingKey = `${session.id}:${currentState.id}`;
    if (voiceOpeningKeyRef.current === openingKey) return;
    voiceOpeningKeyRef.current = openingKey;
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setVoiceStatus("processing");
      setVoiceError(null);
      setVoiceAssistantText("");
      responseStartedRef.current = performance.now();
      startVoiceOpening(session.id, currentState.id, interactionMode === "text", preparedOpeningId)
        .then(async (result) => {
          if (cancelled) return;
          recordResponse("browser_end_to_end");
          setVoiceAssistantText(result.assistantText);
          setVoiceStatus("speaking");
          if (interactionMode === "text") {
            // Text openings never invoke playback, even if an unexpected audio field is returned.
          } else if (!result.avatarSessionActive) {
            await playVoiceAudio(result.tts?.audioPayloadBase64, result.tts?.contentType);
          } else {
            await waitForAvatarSpeech(result.assistantText, session.id, result.avatarDeliveryId);
          }
          if (cancelled) return;
          setVoiceStatus(result.conversationComplete ? "complete" : "idle");
          if (result.conversationComplete) {
            applySession({ ...session, completedStateIds: Array.from(new Set([...session.completedStateIds, currentState.id])) });
          }
        })
        .catch(() => {
          if (!cancelled) {
            setVoiceError(interactionMode === "text" ? "Acilis sorusu getirilemedi. Acilis sorusunu tekrar getir dugmesiyle yeniden dene." : "AI acilis mesaji baslatilamadi. Yaniti yazarak devam edebilirsin.");
            setVoiceStatus("error");
            if (interactionMode === "voice") {
              setPreparedOpening(null);
              setAvatarReady(false);
              void cancelVoiceDelivery(session.id, currentState.id).catch(() => undefined);
            }
          }
        });
    });
    return () => {
      cancelled = true;
    };
  }, [applySession, avatarReady, interactionMode, openingAttempt, preparedOpeningId, currentState, session, playVoiceAudio, waitForAvatarSpeech, recordResponse]);

  function saveTextDraft(value: string) {
    if (!session || !currentState) return;
    const next = { ...drafts, [currentState.id]: value };
    setDrafts(next);
    try {
      window.sessionStorage.setItem(draftStorageKey(session.id), JSON.stringify(next));
    } catch {
      setSubmitError("Yanıt bu sekmede tutuluyor ancak tarayıcıya kaydedilemedi. Sayfayı yenilemeden eğitimi bitir.");
    }
  }

  async function handleTextTurn() {
    if (!session || !currentState || textPending || !textTurn.trim() || (interactionMode === "text" && !voiceAssistantText)) return;
    const requestId = ++textRequestRef.current;
    setTextPending(true);
    responseStartedRef.current = performance.now();
    setSubmitError(null);
    cleanupVoiceTurn();
    setVoiceStatus("idle");
    // Typed live turns, like voice transcripts, remain only in backend TTL context.
    try {
      const result = await submitConversationTurn(session.id, { stateId: currentState.id, learnerText: textTurn.trim(), textOnly: true });
      if (requestId !== textRequestRef.current) return;
      recordResponse("browser_end_to_end");
      setVoiceAssistantText(result.assistantText);
      setTextTurn("");
      setVoiceError(null);
      setVoiceStatus(result.conversationComplete ? "complete" : "idle");
      if (isTrainingSession(result.session)) applySession(result.session);
    } catch (error) {
      if (requestId === textRequestRef.current) setSubmitError(getSubmitErrorMessage(error));
    } finally {
      if (requestId === textRequestRef.current) setTextPending(false);
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

  async function handleFinalize() {
    if (!session || finalizeInFlightRef.current) return;
    finalizeInFlightRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const answers = sortedStates
        .filter((state) => isInteractiveState(state) && !isAvatarState(state))
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
      if (error instanceof ApiError) {
        const detail = (error.payload as { detail?: { missingStateIds?: unknown } } | null)?.detail;
        if (Array.isArray(detail?.missingStateIds)) setMissingStateIds(detail.missingStateIds.filter((id): id is string => typeof id === "string"));
      }
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

  async function handleStartVoiceTurn() {
    if (interactionMode !== "voice" || !session || !currentState || textPending || voiceStartInFlightRef.current || (voiceStatus !== "idle" && voiceStatus !== "error")) return;
    if (session.completedStateIds.includes(currentState.id)) {
      setVoiceError("Bu gorusme adimi zaten tamamlandi.");
      setVoiceStatus("error");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === "undefined") {
      setVoiceError("Bu tarayicida mikrofon kaydi kullanilamiyor.");
      setVoiceStatus("error");
      return;
    }
    const voiceGeneration = textRequestRef.current;
    voiceStartInFlightRef.current = true;
    setVoiceError(null);
    setVoiceAssistantText("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (voiceGeneration !== textRequestRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      mediaStreamRef.current = stream;
      const socket = new WebSocket(websocketUrl(`/api/learner/sessions/${session.id}/voice/stt`));
      let receivedResult = false;
      voiceSocketRef.current = socket;
      socket.binaryType = "arraybuffer";
      socket.onopen = () => {
        if (voiceGeneration !== textRequestRef.current || voiceSocketRef.current !== socket) return;
        socket.send(JSON.stringify({ stateId: currentState.id, accessToken: readSupabaseAccessToken() }));
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
        if (voiceGeneration !== textRequestRef.current || voiceSocketRef.current !== socket) return;
        const payload = JSON.parse(event.data as string) as { type?: string; transcript?: string; result?: { assistantText?: string; conversationComplete?: boolean; avatarSessionActive?: boolean; avatarDeliveryId?: string | null; tts?: { audioPayloadBase64?: string | null; contentType?: string | null } } ; code?: string };
        if (payload.type === "final_transcript" || payload.type === "committed_transcript") {
          setVoiceStatus("processing");
          stopAudioCapture();
        }
        if (payload.type === "voice_turn_result" && payload.result) {
          receivedResult = true;
          recordResponse("browser_end_to_end");
          setVoiceAssistantText(payload.result.assistantText ?? "");
          setVoiceStatus("speaking");
          const playback = payload.result.avatarSessionActive
            ? waitForAvatarSpeech(payload.result.assistantText ?? "", session.id, payload.result.avatarDeliveryId)
            : playVoiceAudio(payload.result.tts?.audioPayloadBase64, payload.result.tts?.contentType);
          void playback.then(() => {
            if (voiceGeneration !== textRequestRef.current) return;
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
        if (voiceGeneration !== textRequestRef.current || voiceSocketRef.current !== socket) return;
        setVoiceError("Ses aktarim baglantisi kurulamadı. Yaniti yazarak devam edebilirsin.");
        setVoiceStatus("error");
        cleanupVoiceTurn();
      };
      socket.onclose = () => {
        if (voiceGeneration !== textRequestRef.current || voiceSocketRef.current !== socket) return;
        voiceStartInFlightRef.current = false;
        if (!receivedResult) {
          stopAudioCapture();
          setVoiceError("Ses bağlantısı kapandı. Mikrofonu tekrar açabilir veya yazarak devam edebilirsin.");
          setVoiceStatus("error");
        }
      };
    } catch (error) {
      cleanupVoiceTurn();
      setVoiceError(error instanceof DOMException && error.name === "NotAllowedError" ? "Mikrofon izni reddedildi." : "Mikrofon baslatilamadi.");
      setVoiceStatus("error");
    }
  }

  function handleStopVoiceTurn() {
    if (voiceStatus === "listening") {
      stopAudioCapture();
      if (voiceSocketRef.current?.readyState === WebSocket.OPEN) voiceSocketRef.current.send("stop");
      responseStartedRef.current = performance.now();
      setVoiceStatus("processing");
    } else {
      cleanupVoiceTurn();
      setVoiceStatus("idle");
    }
  }

  if (!session || !currentState) {
    return <Card className="rounded-lg border-slate-200"><CardContent className="p-6 text-sm text-slate-600">Egitim yukleniyor...</CardContent></Card>;
  }

  if (!interactionMode) {
    return (
      <Card className="mx-auto max-w-2xl rounded-lg border-slate-200">
        <CardHeader><CardTitle>{training?.title ?? "Egitime hazirlik"}</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-slate-600">Baslamadan once egitimin nasil ilerledigini incele ve katilim seklini sec.</p>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>Bilgi adimlarini incele, sorulari kendi deneyimine gore yanitla.</li>
            <li>AI ile pratik adimlarinda acilis sorusunu bekle ve sirayla yanit ver.</li>
            <li>Yanitlarin egitimin sonunda birlikte degerlendirilir; final raporunda puan ve geri bildirim alirsin.</li>
            <li>Egitimi ayni sekmede tamamla. Uzun sure ara verirsen bazi konusma yanitlarini yeniden vermen gerekebilir.</li>
            <li>Secimin bu egitim boyunca kullanilir. Sesli kullanim icin mikrofon izni gerekir.</li>
          </ul>
          <fieldset className="space-y-3">
            <legend className="mb-2 text-sm font-medium">Nasil devam etmek istersin?</legend>
            <label className="flex items-center gap-2 rounded-md border p-3 text-sm">
              <input type="radio" name="training-mode" value="text" checked={briefingMode === "text"} onChange={() => setBriefingMode("text")} />
              Yazili: AI ile yazisarak devam et, mikrofon ve avatar kullanma.
            </label>
            <label className="flex items-center gap-2 rounded-md border p-3 text-sm">
              <input type="radio" name="training-mode" value="voice" checked={briefingMode === "voice"} onChange={() => setBriefingMode("voice")} />
              Sesli: Avatar ile konusarak devam et.
            </label>
          </fieldset>
          <Button onClick={startTraining}>Egitime Basla</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col px-4 pb-12 sm:px-6">
      <header className="py-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-teal-700">
              <span>Canlı eğitim</span>
              <span className="h-1 w-1 rounded-full bg-slate-300" />
              <span>{training?.durationMin ?? session.usage.totalDurationMin} min</span>
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-slate-950">{training?.title ?? "AkademX10 Training"}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {training?.description ?? "Adımları tamamla, AI koçla pratik yap ve final değerlendirmeyi tek seferde başlat."}
            </p>
          </div>
          <div className="w-full rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:w-80">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">İlerleme</span>
              <span className="font-semibold text-slate-950">{progress.completed}/{progress.total}</span>
            </div>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-teal-600 transition-all" style={{ width: `${progress.percent}%` }} />
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
              <span>%{progress.percent} tamamlandı</span>
              <span>Finalde AI raporu</span>
            </div>
          </div>
        </div>
      </header>

      <main className="grid flex-1 gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <LearningPath states={sortedStates} currentStateId={currentState.id} completedStateIds={session.completedStateIds} />

        <section className="space-y-6">
          {isAvatarState(currentState) && interactionMode === "voice" && !preparedOpeningId && voiceStatus !== "error" && !session.completedStateIds.includes(currentState.id) ? <p role="status" className="rounded-lg bg-slate-50 p-4 text-sm">Acilis hazirlaniyor. Avatar hazir oldugunda baglanacak.</p> : null}
          {isAvatarState(currentState) && interactionMode === "voice" && preparedOpeningId && (!session.completedStateIds.includes(currentState.id) || voiceStatus === "speaking") ? (
            <LiveAvatarView
              key={`${session.id}:${currentState.id}`}
              onPlaybackStarted={() => recordResponse("browser_playback")}
              sessionId={session.id}
              stateId={currentState.id}
              isSpeaking={voiceStatus === "speaking"}
              isListening={voiceStatus === "listening"}
              isCompleted={session.completedStateIds.includes(currentState.id) || voiceStatus === "complete"}
              assistantText={voiceAssistantText}
              onAvatarReady={() => setAvatarReady(true)}
              onAvatarError={(error) => {
                setAvatarReady(false);
                setVoiceError(error);
                setVoiceStatus("error");
                setPreparedOpening(null);
                void cancelVoiceDelivery(session.id, currentState.id).catch(() => undefined);
              }}
            />
          ) : null}

          <Card className="rounded-lg border-slate-200">
            <CardHeader className="space-y-4 border-b border-slate-100">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={stateModeClass(currentState.type)}>{stateModeLabel(currentState.type)}</Badge>
                    <Badge variant="secondary">{stateTypeLabel(currentState.type)}</Badge>
                    <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                      <Clock className="h-3.5 w-3.5" />
                      {currentState.estimatedMin} min
                    </span>
                  </div>
                  <CardTitle className="mt-3 text-2xl">{currentState.title}</CardTitle>
                </div>
                <Badge className={session.completedStateIds.includes(currentState.id) ? "bg-emerald-700 text-white" : "bg-slate-950 text-white"}>
                  Adım {currentState.order} / {sortedStates.length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6 p-6">
              <DynamicStateContent state={currentState} />


              {isAvatarState(currentState) && interactionMode === "voice" ? (
                <VoicePocBox
                  status={voiceStatus}
                  error={voiceError}
                  disabled={!preparedOpeningId || !avatarReady || textPending || session.completedStateIds.includes(currentState.id) || voiceStatus === "complete"}
                  onStart={handleStartVoiceTurn}
                  onStop={handleStopVoiceTurn}
                />
              ) : null}

              {isAvatarState(currentState) && (interactionMode === "voice" || !voiceAssistantText) && voiceStatus === "error" ? <Button variant="outline" onClick={async () => {
                const retryGeneration = textRequestRef.current;
                setVoiceStatus("processing");
                if (interactionMode === "voice") {
                  try { await cancelVoiceDelivery(session.id, currentState.id); }
                  catch { if (retryGeneration === textRequestRef.current) { setVoiceStatus("error"); setVoiceError("Hazirlik sifirlanamadi. Tekrar dene."); } return; }
                }
                if (retryGeneration !== textRequestRef.current) return;
                preparationRef.current = null;
                voiceOpeningKeyRef.current = null;
                setPreparedOpening(null);
                setAvatarReady(false);
                setOpeningAttempt((attempt) => attempt + 1);
              }}>Acilis sorusunu tekrar getir</Button> : null}
              {voiceError ? <p role="alert" className="text-sm text-amber-900">{voiceError}</p> : null}
              {voiceAssistantText ? <p aria-live="polite" className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm">{voiceAssistantText}</p> : null}
              {(isInteractiveState(currentState) || isAvatarState(currentState)) && (!isAvatarState(currentState) || interactionMode !== null) ? (
                <div className="space-y-3">
                  {!isAvatarState(currentState) ? <p className="whitespace-pre-wrap text-sm text-slate-700">{currentState.prompt}</p> : null}
                  <label htmlFor="training-answer" className="block text-sm font-medium">
                    {isAvatarState(currentState) ? "Yazarak devam et" : "Yanıtın"}
                  </label>
                  <textarea
                    id="training-answer"
                    className="min-h-28 w-full rounded-md border border-slate-300 p-3 text-sm"
                    maxLength={isAvatarState(currentState) ? 2000 : 4000}
                    value={isAvatarState(currentState) ? textTurn : drafts[currentState.id] ?? ""}
                    disabled={isSubmitting || textPending || session.status === "completed" || (isAvatarState(currentState) && interactionMode === "text" && !voiceAssistantText)}
                    onChange={(event) => isAvatarState(currentState) ? setTextTurn(event.target.value) : saveTextDraft(event.target.value)}
                  />
                  {isAvatarState(currentState) ? (
                    <Button onClick={handleTextTurn} disabled={!textTurn.trim() || (interactionMode === "text" && !voiceAssistantText) || textPending || isSubmitting || voiceStatus === "listening" || voiceStatus === "processing" || voiceStatus === "speaking" || session.completedStateIds.includes(currentState.id)}>
                      {textPending ? "Yanıt hazırlanıyor..." : "Yazılı yanıt gönder"}
                    </Button>
                  ) : <p className="text-xs text-slate-500">Yanıtın bu sekmede saklanır ve eğitim sonunda değerlendirilir.</p>}
                </div>
              ) : null}
              {session.completedAt ? <a className="font-medium text-teal-700 underline" href={`/learner/sessions/${session.id}/report`}>Final raporunu aç</a> : null}

              {submitError ? (
                <div role="alert" className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
                  {submitError}
                  {missingStateIds.map((id) => {
                    const missing = sortedStates.find((state) => state.id === id);
                    return missing ? <Button key={id} variant="outline" className="m-1" disabled={isSubmitting} onClick={async () => {
                      setIsSubmitting(true);
                      try {
                        const recovered = await recoverConversationState(session.id, id);
                        applySession(recovered);
                        setMissingStateIds([]);
                      } catch (error) { setSubmitError(getSubmitErrorMessage(error)); }
                      finally { setIsSubmitting(false); }
                    }}>Adim {missing.order}: {missing.title} - yeniden yanitla</Button> : null;
                  })}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-5">
                <Button variant="outline" onClick={handleMovePrevious} disabled={textPending || isSubmitting || !canMovePrevious(session, sortedStates)}>
                  <ArrowLeft className="h-4 w-4" />
                  Önceki
                </Button>
                <Button variant="secondary" onClick={handleComplete} disabled={textPending || isSubmitting || session.completedStateIds.includes(currentState.id)}>
                  <CheckCircle2 className="h-4 w-4" />
                  Tamamla
                </Button>
                <Button onClick={handleMoveNext} disabled={textPending || isSubmitting || !canMoveNext(session, sortedStates)}>
                  Sonraki
                  <ArrowRight className="h-4 w-4" />
                </Button>
                {currentState.type === "final" ? (
                  <Button type="button" onClick={handleFinalize} disabled={isSubmitting || Boolean(session.completedAt)}>
                    <Sparkles className="h-4 w-4" />
                    {isSubmitting ? "Tamamlanıyor..." : "Eğitimi Bitir"}
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

function LearningPath({
  states,
  currentStateId,
  completedStateIds,
}: {
  states: TrainingState[];
  currentStateId: string;
  completedStateIds: string[];
}) {
  return (
    <aside className="h-fit rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-4">
      <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
        <ListChecks className="h-4 w-4 text-teal-700" />
        <p className="font-semibold text-slate-950">Eğitim akışı</p>
      </div>
      <div className="mt-4 space-y-2">
        {states.map((state) => {
          const complete = completedStateIds.includes(state.id);
          const current = state.id === currentStateId;
          return (
            <div
              key={state.id}
              className={`rounded-md border px-3 py-2 ${
                current
                  ? "border-teal-300 bg-teal-50"
                  : complete
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex items-start gap-2">
                <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${complete ? "bg-emerald-700 text-white" : current ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-600"}`}>
                  {complete ? <CheckCircle2 className="h-3.5 w-3.5" /> : state.order}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-950">{state.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${stateModeClass(state.type)}`}>{stateModeLabel(state.type)}</span>
                    <span className="text-xs text-slate-500">{stateTypeLabel(state.type)} - {state.estimatedMin} min</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function draftStorageKey(sessionId: string) {
  return `akademx10.sessionDraft.${sessionId}`;
}

function readSessionDrafts(sessionId: string): Record<string, string> {
  try {
    const raw = window.sessionStorage.getItem(draftStorageKey(sessionId));
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).filter(([, value]) => typeof value === "string")) as Record<string, string>;
  } catch {
    return {};
  }
}

function clearSessionDrafts(sessionId: string) {
  try {
    window.sessionStorage.removeItem(draftStorageKey(sessionId));
  } catch {
    // The evaluation has already completed; storage availability must not undo it.
  }
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
  if (state.type === "video" || state.type === "final") return <VideoStateContent />;
  return null;
}

function VideoStateContent() {
  return (
    <div className="aspect-video overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
      <div className="flex h-full items-center justify-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-white/10">
          <PlayCircle className="h-8 w-8 text-white/80" />
        </div>
      </div>
      <div className="flex h-10 items-center gap-3 border-t border-white/10 bg-black/30 px-4">
        <div className="h-1.5 flex-1 rounded-full bg-white/15" />
        <div className="h-1.5 w-10 rounded-full bg-white/15" />
      </div>
    </div>
  );
}

function stateTypeLabel(type: TrainingState["type"]) {
  const labels: Record<TrainingState["type"], string> = {
    intro: "Tanıtım",
    video: "Eğitim",
    avatar: "Avatar",
    live_avatar: "Avatar",
    question: "Yazılı pratik",
    roleplay: "Vaka / Roleplay",
    reflection: "Aksiyon listesi",
    feedback: "Geri bildirim",
    final: "Kapanış",
  };
  return labels[type];
}

function stateModeLabel(type: TrainingState["type"]) {
  return type === "video" || type === "intro" || type === "final" ? "Video" : "AI";
}

function stateModeClass(type: TrainingState["type"]) {
  return stateModeLabel(type) === "Video"
    ? "bg-orange-500 text-white hover:bg-orange-500"
    : "bg-violet-700 text-white hover:bg-violet-700";
}

function VoicePocBox({
  status,
  error,
  disabled,
  onStart,
  onStop,
}: {
  status: VoiceStatus;
  error: string | null;
  disabled: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  const isListening = status === "listening";
  const isWaiting = status === "processing" || status === "speaking";
  const label = isListening ? "Konusmayi bitir" : "Mikrofonu ac";
  const hint = error ?? (status === "speaking" ? "Avatar konusurken mikrofon kapali" : status === "processing" ? "Ses isleniyor" : disabled || status === "complete" ? "Gorusme tamamlandi" : label);

  return (
    <div className="flex justify-center py-5">
      <Button
        type="button"
        aria-label={label}
        title={hint}
        onClick={isListening ? onStop : onStart}
        disabled={disabled || isWaiting}
        className={`h-20 w-20 rounded-full p-0 shadow-lg transition ${
          isListening
            ? "bg-red-600 text-white shadow-red-200 hover:bg-red-700"
            : "bg-sky-500 text-white shadow-sky-200 hover:bg-sky-600"
        } disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none`}
      >
        <Mic className="h-10 w-10" />
      </Button>
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
  if (code?.includes("quota")) return "Ses hizmetinin kredisi tukendi. Yazarak devam edebilirsin.";
  if (code?.includes("rate_limit")) return "Ses hizmeti su an yogun. Biraz sonra tekrar dene veya yazarak devam et.";
  if (code?.includes("timeout")) return "Ses hizmeti zamaninda yanit vermedi. Yazarak devam edebilirsin.";
  if (code?.includes("empty_audio")) return "Ses uretilemedi. Yanit metnini okuyarak devam edebilirsin.";
  if (code === "stt_provider_not_configured") return "Ses tanima servisi yapilandirilmamis. Yaniti yazarak devam edebilirsin.";
  if (code === "empty_transcript") return "Net bir konusma algilanamadi. Tekrar dene veya yanitini yaz.";
  if (code === "session_not_found" || code === "state_not_found") return "Bu sesli gorusme artik kullanilamiyor.";
  return "Sesli gorusme tamamlanamadi. Yaniti yazarak devam edebilirsin.";
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
  if (code === "missing_session_answers") return "Bazi yanitlar artik mevcut degil. Asagidaki adimlara donup yeniden yanitlayabilirsin.";
    if (code === "evaluation_processing") return "Değerlendirme devam ediyor. Yanıtların korundu; biraz sonra Eğitimi Bitir düğmesine tekrar bas.";
    if (code === "invalid_finalization_payload") return "Değerlendirilecek yanıt eksik veya konuşma süresi dolmuş olabilir. Önceki adımlardaki yanıtlarını kontrol edip tekrar dene.";
    if (error.status === 429 || code === "max_queries_per_state") {
      return "Bu adım AI geri bildirim limitine ulaştı. Yanıtın silinmedi; sonraki adıma geçebilir veya eğitimi baştan başlatabilirsin.";
    }
    if (error.status === 422) return "Bu yanit henuz degerlendirilemiyor. Yaniti kontrol edip tekrar gonder.";
    if (error.status === 0) return "Degerlendirme servisine ulasilamadi.";
  }
  return "Yanit gonderilemedi. Yazdigin metin silinmedi.";
}

function extractApiErrorCode(payload: unknown) {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (!detail || typeof detail !== "object" || !("code" in detail)) return null;
  const code = (detail as { code?: unknown }).code;
  return typeof code === "string" ? code : null;
}

function isTrainingSession(value: unknown): value is TrainingSession {
  return Boolean(value && typeof value === "object" && "completedStateIds" in value && "usage" in value);
}
