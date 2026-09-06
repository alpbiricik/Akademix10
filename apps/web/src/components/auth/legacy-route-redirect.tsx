"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { roleDestinations } from "@/lib/auth-types";
import { getTrustedProfile } from "@/lib/supabase-auth";

export function LegacyRouteRedirect({ fallback = "/login" }: { fallback?: string }) {
  const router = useRouter();

  useEffect(() => {
    getTrustedProfile()
      .then((user) => router.replace(roleDestinations[user.role]))
      .catch(() => router.replace(fallback));
  }, [fallback, router]);

  return null;
}
