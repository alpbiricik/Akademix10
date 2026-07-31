export const TOTAL_SESSION_DURATION_MIN = 40;
export const AVATAR_ACTIVE_TARGET_MIN = 7;
export const AVATAR_OPEN_CLOSE_TARGET = 10;
export const AVATAR_BUFFER_MULTIPLIER = 1.15;
export const BUFFERED_AVATAR_BILLABLE_MIN = 8.05;
export const LIVE_AVATAR_LITE_CREDIT_PRICE_USD = 0.099;
export const SAFE_AVATAR_ROUNDING_COST_USD = 0.99;
export const SAFE_TOTAL_SESSION_BUDGET_USD = 1.25;

export type CostComponent =
  | "llm_tokens"
  | "stt_minutes"
  | "tts_characters"
  | "live_avatar_lite"
  | "platform_buffer";

export interface AvatarUsageLog {
  activeSeconds: number;
  openCount: number;
  closeCount: number;
  bufferedBillableMin: number;
}

export interface TokenUsageLog {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  modelName?: string;
}

export interface VoiceUsageLog {
  sttMinutes: number;
  ttsCharacters: number;
  sttProvider?: string;
  ttsProvider?: string;
}

export interface SessionCostBreakdown {
  sessionId: string;
  totalSessionDurationMin: number;
  avatar: AvatarUsageLog;
  tokens: TokenUsageLog;
  voice: VoiceUsageLog;
  estimatedAvatarCostUsd: number;
  safeAvatarCostUsd: number;
  estimatedTotalCostUsd: number;
  safeTotalBudgetUsd: number;
  components: CostComponent[];
}

export function calculateBufferedAvatarMin(activeMin: number): number {
  return roundToTwoDecimals(activeMin * AVATAR_BUFFER_MULTIPLIER);
}

export function calculateAvatarCost(activeMin: number): number {
  return roundToTwoDecimals(calculateBufferedAvatarMin(activeMin) * LIVE_AVATAR_LITE_CREDIT_PRICE_USD);
}

export function calculateSafeSessionBudget(): number {
  return SAFE_TOTAL_SESSION_BUDGET_USD;
}

function roundToTwoDecimals(value: number): number {
  return Math.round(value * 100) / 100;
}
