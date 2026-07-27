"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MOCK_USER_STORAGE_KEY, parseMockUser, roleDestinations } from "@/lib/mock-auth";

export function LegacyRouteRedirect({
  target,
  title = "This route moved",
  description = "AkademX10 now uses role-specific workspaces.",
}: {
  target?: string;
  title?: string;
  description?: string;
}) {
  const router = useRouter();
  const [fallbackHref, setFallbackHref] = useState("/login");

  useEffect(() => {
    const user = parseMockUser(window.localStorage.getItem(MOCK_USER_STORAGE_KEY));
    const destination = target ?? (user ? roleDestinations[user.role] : "/login");
    setFallbackHref(destination);
    router.replace(destination);
  }, [router, target]);

  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <p className="max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
        <Link href={fallbackHref} className="inline-flex h-9 shrink-0 items-center justify-center rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
          Continue
        </Link>
      </CardContent>
    </Card>
  );
}
