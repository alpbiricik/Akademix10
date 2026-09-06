"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { roleDestinations } from "@/lib/auth-types";
import { signInWithPassword } from "@/lib/supabase-auth";

export function LoginForm() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin() {
    setError(null);
    setSubmitting(true);
    try {
      const profile = await signInWithPassword(identifier.trim(), password);
      router.push(roleDestinations[profile.role]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed. Check your credentials and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="login-identifier">Email</Label>
        <Input id="login-identifier" type="email" value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="email" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="login-password">Password</Label>
        <Input id="login-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
      </div>
      {error ? <p className="text-sm font-medium text-red-700">{error}</p> : null}
      <Button type="button" className="w-full bg-slate-950 text-white hover:bg-slate-800" onClick={handleLogin} disabled={submitting || !identifier.trim() || !password}>
        <LogIn className="h-4 w-4" />
        {submitting ? "Signing in..." : "Sign in"}
      </Button>
    </div>
  );
}
