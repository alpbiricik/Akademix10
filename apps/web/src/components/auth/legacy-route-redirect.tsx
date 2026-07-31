"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { MOCK_USER_STORAGE_KEY, parseMockUser, roleDestinations } from "@/lib/mock-auth";

export function LegacyRouteRedirect({ fallback = "/login" }: { fallback?: string }) {
  const router = useRouter();

  useEffect(() => {
    const user = parseMockUser(window.localStorage.getItem(MOCK_USER_STORAGE_KEY));
    router.replace(user ? roleDestinations[user.role] : fallback);
  }, [fallback, router]);

  return null;
}
