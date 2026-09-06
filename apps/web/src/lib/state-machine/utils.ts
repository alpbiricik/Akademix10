import type { UserRole } from "@/lib/auth-types";
import type { TrainingState, TrainingStateType } from "@/lib/state-machine/types";

export function sortStatesByOrder(states: TrainingState[]) {
  return [...states].sort((a, b) => a.order - b.order);
}

export function getProgressPercent(completed: number, total: number) {
  if (total <= 0) return 0;
  return Math.round((completed / total) * 100);
}

export function formatDuration(minutes: number) {
  return `${minutes} min`;
}

export function getStateTypeLabel(type: TrainingStateType) {
  const labels: Record<TrainingStateType, string> = {
    intro: "Intro",
    video: "Video",
    avatar: "Avatar",
    live_avatar: "Live Avatar",
    question: "Question",
    roleplay: "Roleplay",
    reflection: "Reflection",
    feedback: "Feedback",
    final: "Final",
  };
  return labels[type];
}

export function getStateTypeTone(type: TrainingStateType) {
  const tones: Record<TrainingStateType, string> = {
    intro: "bg-slate-100 text-slate-800",
    video: "bg-sky-50 text-sky-800",
    avatar: "bg-teal-50 text-teal-800",
    live_avatar: "bg-teal-50 text-teal-800",
    question: "bg-indigo-50 text-indigo-800",
    roleplay: "bg-amber-50 text-amber-900",
    reflection: "bg-violet-50 text-violet-800",
    feedback: "bg-emerald-50 text-emerald-800",
    final: "bg-slate-900 text-white",
  };
  return tones[type];
}

export function isInteractiveState(state: TrainingState) {
  return state.type === "question" || state.type === "roleplay" || state.type === "reflection";
}

export function isAvatarState(state: TrainingState) {
  return Boolean(state.avatarEnabled || state.type === "avatar" || state.type === "live_avatar" || state.type === "roleplay");
}


export function clampScore(score: number) {
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function getRoleLabel(role: UserRole) {
  if (role === "platform") return "Platform / AkademX10 Team";
  if (role === "company") return "Company / HR Manager";
  return "Learner / Employee";
}

export function formatUsd(val: number) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val); }
