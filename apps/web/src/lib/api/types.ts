export type ApiMethod = "GET" | "POST" | "PATCH";

export interface ApiEndpoint {
  method: ApiMethod;
  path: string;
}

export interface ApiRequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
}

export interface SessionStateUpdatePayload {
  action: "complete" | "next" | "previous";
}

export interface SessionAnswerPayload {
  stateId: string;
  answerText: string;
}

export interface SessionFinalizePayload {
  idempotencyKey: string;
  contractVersion: "2.0";
  answers: SessionAnswerPayload[];
  sessionVersion?: string;
}
