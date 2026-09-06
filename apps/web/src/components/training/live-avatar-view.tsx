"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, RefreshCw, Video, VideoOff, Volume2, Wifi } from "lucide-react";
import { Track } from "livekit-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { acquireAvatarSession, releaseAvatarSession } from "@/lib/avatar-session-manager";

export interface LiveAvatarViewProps {
  sessionId: string;
  stateId: string;
  isSpeaking: boolean;
  isListening: boolean;
  isCompleted: boolean;
  assistantText?: string;
  onAvatarError?: (error: string) => void;
  onAvatarReady?: () => void;
}

export function LiveAvatarView({
  sessionId,
  stateId,
  isSpeaking,
  isListening,
  assistantText,
  onAvatarError,
  onAvatarReady,
}: LiveAvatarViewProps) {
  const [status, setStatus] = useState<"idle" | "connecting" | "streaming" | "error">("idle");
  const [isStarted, setIsStarted] = useState(true);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const initInFlightRef = useRef(false);
  const videoReadyRef = useRef(false);
  
  const onAvatarErrorRef = useRef(onAvatarError);
  const onAvatarReadyRef = useRef(onAvatarReady);
  useEffect(() => {
    onAvatarErrorRef.current = onAvatarError;
  }, [onAvatarError]);
  useEffect(() => {
    onAvatarReadyRef.current = onAvatarReady;
  }, [onAvatarReady]);

  useEffect(() => {
    videoReadyRef.current = false;
  }, [sessionId, stateId]);

  const markAvatarVideoReady = useCallback(() => {
    if (videoReadyRef.current) return;
    videoReadyRef.current = true;
    setStatus("streaming");
    onAvatarReadyRef.current?.();
  }, []);

  const initAvatar = useCallback(async () => {
    if (initInFlightRef.current) return;
    initInFlightRef.current = true;
    setStatus("connecting");

    try {
      const attachVideoTrack = (track: Track) => {
        if (track.kind === Track.Kind.Video && videoRef.current) {
          const video = track.attach(videoRef.current) as HTMLVideoElement;
          const markReadyAfterPlay = () => {
            void video.play().finally(markAvatarVideoReady);
          };
          if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
            markReadyAfterPlay();
          } else {
            video.onloadeddata = markReadyAfterPlay;
            video.oncanplay = markReadyAfterPlay;
          }
        }
        if (track.kind === Track.Kind.Audio && audioRef.current) {
          track.attach(audioRef.current);
          void audioRef.current.play().catch(() => undefined);
        }
      };

      const handleDisconnected = () => {
        videoReadyRef.current = false;
        setStatus("idle");
      };

      const session = await acquireAvatarSession(sessionId, stateId, attachVideoTrack, handleDisconnected);
      if (!videoReadyRef.current) {
        setStatus(session.status === "error" ? "error" : "connecting");
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Could not connect to LiveAvatar.";
      setStatus("error");
      onAvatarErrorRef.current?.(msg);
    } finally {
      initInFlightRef.current = false;
    }
  }, [sessionId, stateId, markAvatarVideoReady]);

  const stopAvatar = useCallback(async () => {
    releaseAvatarSession(sessionId, stateId);
    setStatus("idle");
  }, [sessionId, stateId]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      if (isStarted) {
        void initAvatar();
      } else {
        void stopAvatar();
      }
    });
    return () => {
      cancelled = true;
      void stopAvatar();
    };
  }, [initAvatar, isStarted, stopAvatar]);


  const handleToggle = () => {
    setIsStarted((prev) => !prev);
  };

  const handleRetry = () => {
    void initAvatar();
  };

  return (
    <div className="relative overflow-hidden rounded-xl border border-teal-200 bg-linear-to-b from-slate-900 to-slate-950 p-4 text-white shadow-md">
      <audio ref={audioRef} autoPlay />
      {/* Header & Badges */}

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-teal-400" />
          <span className="text-sm font-semibold tracking-wide text-slate-100">Interactive Avatar</span>
          {status === "streaming" && (
            <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
              <Wifi className="mr-1 h-3 w-3 animate-pulse text-emerald-400" /> Live Video
            </Badge>
          )}
          {status === "connecting" && (
            <Badge variant="outline" className="text-amber-300 border-amber-400/30">
              <RefreshCw className="mr-1 h-3 w-3 animate-spin" /> Connecting...
            </Badge>
          )}
          {status === "error" && (
            <Badge variant="outline" className="text-rose-300 border-rose-400/30">
              Audio Fallback Active
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            className="h-7 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            {isStarted ? (
              <>
                <VideoOff className="mr-1 h-3.5 w-3.5 text-slate-400" /> Disable Avatar
              </>
            ) : (
              <>
                <Video className="mr-1 h-3.5 w-3.5 text-teal-400" /> Enable Avatar
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main Avatar Viewport */}
      <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg bg-slate-900 border border-slate-800">
        {/* Real WebRTC Video Element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`h-full w-full object-cover transition-opacity duration-300 ${
            status === "streaming" ? "opacity-100" : "opacity-0 absolute pointer-events-none"
          }`}
        />

        {/* Live Speaking Indicator Overlay on Video */}
        {status === "streaming" && isSpeaking && (
          <div className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-slate-950/80 px-3 py-1 text-xs backdrop-blur-xs text-teal-300 border border-teal-500/40 shadow-lg">
            <span className="h-2 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:0ms]" />
            <span className="h-3 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:150ms]" />
            <span className="h-2.5 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:300ms]" />
            <Volume2 className="ml-1 h-3.5 w-3.5 text-teal-400" />
            <span className="font-medium text-slate-200">Speaking...</span>
          </div>
        )}


        {/* Avatar unavailable or connecting display */}
        {(status === "connecting" || status === "idle" || status === "error") && (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            {/* Avatar Persona Icon with animated pulse */}
            <div className="relative flex items-center justify-center">
              <div
                className={`absolute h-24 w-24 rounded-full transition-all duration-500 ${
                  isSpeaking
                    ? "animate-ping bg-teal-500/30"
                    : isListening
                    ? "animate-pulse bg-amber-500/20"
                    : "bg-teal-500/10"
                }`}
              />
              <div
                className={`relative z-10 flex h-20 w-20 items-center justify-center rounded-full border-2 shadow-inner transition-colors duration-300 ${
                  isSpeaking
                    ? "border-teal-400 bg-teal-950/80 text-teal-300"
                    : isListening
                    ? "border-amber-400 bg-amber-950/80 text-amber-300"
                    : "border-slate-700 bg-slate-800 text-slate-300"
                }`}
              >
                <Bot className="h-10 w-10" />
              </div>
            </div>

            {/* Speaking / Listening State indicator */}
            <div className="mt-4 flex flex-col items-center">
              <p className="text-sm font-medium text-slate-200">
                {isSpeaking
                  ? "Avatar is speaking..."
                  : isListening
                  ? "Listening to your answer..."
                  : status === "connecting"
                  ? "Initializing streaming avatar..."
                  : status === "error"
                  ? "Avatar streaming unavailable"
                  : "Avatar is ready"}
              </p>

              {/* Waveform Animation for Speech */}
              {isSpeaking && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="h-3 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:0ms]" />
                  <span className="h-5 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:150ms]" />
                  <span className="h-4 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:300ms]" />
                  <span className="h-6 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:450ms]" />
                  <span className="h-3 w-1 animate-bounce rounded-full bg-teal-400 [animation-delay:200ms]" />
                  <Volume2 className="ml-1 h-3.5 w-3.5 text-teal-400" />
                </div>
              )}

              {/* Error fallback prompt */}
              {status === "error" && (
                <div className="mt-2 flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleRetry}
                    className="h-7 text-xs border-slate-700 text-slate-300 hover:bg-slate-800"
                  >
                    Retry Connection
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Live Assistant Subtitles / Context Banner */}
      {assistantText && (
        <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/90 px-3.5 py-2.5 text-xs leading-5 text-slate-300">
          <span className="font-semibold text-teal-400">Persona: </span>
          {assistantText}
        </div>
      )}
    </div>
  );
}
