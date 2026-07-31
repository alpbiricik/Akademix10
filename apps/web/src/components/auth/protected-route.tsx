"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { LockKeyhole } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  MOCK_USER_STORAGE_KEY,
  parseMockUser,
  roleDestinations,
  roleLabels,
  type MockRole,
  type MockUserSession,
} from "@/lib/mock-auth";

export function ProtectedRoute({
  allowedRoles,
  children,
}: {
  allowedRoles: MockRole[];
  children: ReactNode;
}) {
  const [user, setUser] = useState<MockUserSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      setUser(parseMockUser(window.localStorage.getItem(MOCK_USER_STORAGE_KEY)));
      setReady(true);
    });
  }, []);

  if (!ready) {
    return (
      <Card className="rounded-lg border-slate-200">
        <CardContent className="p-6 text-sm text-slate-600">Checking workspace access...</CardContent>
      </Card>
    );
  }

  if (!user) {
    return (
      <AccessCard
        title="Login required"
        description="Choose an account type before entering this product area."
        primaryHref="/login"
        primaryLabel="Go to Login"
      />
    );
  }

  if (!allowedRoles.includes(user.role)) {
    return (
      <AccessCard
        title="This area is not available for your role"
        description={`You are signed in as ${roleLabels[user.role]}. AkademX10 keeps platform administration, company administration, and learner workspaces separate.`}
        primaryHref={roleDestinations[user.role]}
        primaryLabel={`Go to ${roleLabels[user.role]} Home`}
      />
    );
  }

  return children;
}

function AccessCard({
  title,
  description,
  primaryHref,
  primaryLabel,
}: {
  title: string;
  description: string;
  primaryHref: string;
  primaryLabel: string;
}) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-slate-100 p-2 text-slate-700">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <CardTitle>{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
        <Link href={primaryHref} className="inline-flex h-9 shrink-0 items-center justify-center rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
          {primaryLabel}
        </Link>
      </CardContent>
    </Card>
  );
}
