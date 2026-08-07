import { API_BASE_URL } from "@/lib/api/config";
import { ApiError, normalizeApiError } from "@/lib/api/errors";
import type { ApiRequestOptions } from "@/lib/api/types";

async function apiRequest<T>(method: "GET" | "POST" | "PATCH", path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };

  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.mockRole) headers["x-mock-role"] = options.mockRole;
  if (typeof window !== "undefined") {
    try {
      const rawSession = window.localStorage.getItem("akademx10.supabaseSession");
      const accessToken = rawSession ? (JSON.parse(rawSession) as { accessToken?: string }).accessToken : null;
      if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    } catch {
      window.localStorage.removeItem("akademx10.supabaseSession");
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      throw new ApiError(`API request failed: ${method} ${path}`, response.status, payload);
    }

    return payload as T;
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export function apiGet<T>(path: string, options?: ApiRequestOptions) {
  return apiRequest<T>("GET", path, options);
}

export function apiPost<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, "body"> = {}) {
  return apiRequest<T>("POST", path, { ...options, body });
}

export function apiPatch<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, "body"> = {}) {
  return apiRequest<T>("PATCH", path, { ...options, body });
}
