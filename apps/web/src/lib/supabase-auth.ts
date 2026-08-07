"use client";

import { API_BASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL } from "@/lib/api/config";
import type { MockRole, MockUserSession } from "@/lib/mock-auth";

export const SUPABASE_SESSION_STORAGE_KEY = "akademx10.supabaseSession";

interface StoredSupabaseSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export function getStoredAccessToken() {
  if (typeof window === "undefined") return null;
  const session = readStoredSession();
  return session?.accessToken ?? null;
}

export function readStoredSession(): StoredSupabaseSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SUPABASE_SESSION_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredSupabaseSession) : null;
  } catch {
    return null;
  }
}

function saveStoredSession(session: StoredSupabaseSession) {
  window.localStorage.setItem(SUPABASE_SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  if (typeof window !== "undefined") window.localStorage.removeItem(SUPABASE_SESSION_STORAGE_KEY);
}

async function authRequest(path: string, body: unknown) {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) throw new Error("Supabase public configuration is missing.");
  const response = await fetch(`${SUPABASE_URL.replace(/\/$/, "")}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_PUBLISHABLE_KEY,
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error("Login failed.");
  return payload;
}

export async function signInWithPassword(identifier: string, password: string) {
  const payload = await authRequest("/auth/v1/token?grant_type=password", {
    email: identifier,
    password,
  });
  saveStoredSession({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: Math.floor(Date.now() / 1000) + (payload.expires_in ?? 3600),
  });
  return getTrustedProfile();
}

export async function refreshStoredSession() {
  const session = readStoredSession();
  if (!session?.refreshToken) return null;
  const payload = await authRequest("/auth/v1/token?grant_type=refresh_token", {
    refresh_token: session.refreshToken,
  });
  saveStoredSession({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: Math.floor(Date.now() / 1000) + (payload.expires_in ?? 3600),
  });
  return getTrustedProfile();
}

export async function getTrustedProfile(): Promise<MockUserSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${getStoredAccessToken()}`,
    },
  });
  if (!response.ok) throw new Error("Session is not authorized.");
  const profile = (await response.json()) as { id: string; name?: string; role: MockRole; title?: string; companyId?: string };
  return {
    id: profile.id,
    name: profile.name || "AkademX10 User",
    role: profile.role,
    title: profile.title || "",
    companyId: profile.companyId,
  };
}

export async function signOut() {
  const token = getStoredAccessToken();
  if (token && SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY) {
    await fetch(`${SUPABASE_URL.replace(/\/$/, "")}/auth/v1/logout`, {
      method: "POST",
      headers: {
        apikey: SUPABASE_PUBLISHABLE_KEY,
        Authorization: `Bearer ${token}`,
      },
    }).catch(() => undefined);
  }
  clearStoredSession();
}
