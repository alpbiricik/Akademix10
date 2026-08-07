"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DATA_SOURCE_MODE } from "@/lib/api/config";
import { MOCK_USER_STORAGE_KEY, roleDestinations, type MockRole } from "@/lib/mock-auth";
import { signInWithPassword } from "@/lib/supabase-auth";

const roleOptions: Array<{
  role: MockRole;
  title: string;
  description: string;
  destination: string;
  userId: string;
  companyId?: string;
}> = [
  {
    role: "platform",
    title: "Platform / AkademX10 Team",
    description: "Create templates, manage companies, assign trainings, and monitor platform usage.",
    destination: "/platform/dashboard",
    userId: "user-platform-demo",
  },
  {
    role: "company",
    title: "Company / HR Manager",
    description: "Manage employees, assigned trainings, enrollments, reports, and company usage.",
    destination: "/company/dashboard",
    userId: "user-company-demo",
    companyId: "company-demo",
  },
  {
    role: "learner",
    title: "Learner / Employee",
    description: "Access assigned trainings, training sessions, AI feedback, and your own report.",
    destination: "/learner/dashboard",
    userId: "user-learner-demo",
    companyId: "company-demo",
  },
];

export function MockLoginForm() {
  const router = useRouter();
  const [role, setRole] = useState<MockRole>("learner");
  const [name, setName] = useState("Alp");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSupabaseLogin() {
    setError(null);
    setSubmitting(true);
    try {
      const profile = await signInWithPassword(identifier.trim(), password);
      router.push(roleDestinations[profile.role]);
    } catch {
      setError("Login failed. Check your credentials and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleContinue() {
    const selectedRole = roleOptions.find((option) => option.role === role) ?? roleOptions[0];

    window.localStorage.setItem(
      MOCK_USER_STORAGE_KEY,
      JSON.stringify({
        id: selectedRole.userId,
        name: name.trim() || "Demo User",
        role: selectedRole.role,
        title: selectedRole.title,
        companyId: selectedRole.companyId,
      })
    );

    router.push(selectedRole.destination);
  }

  if (DATA_SOURCE_MODE === "api") {
    return (
      <div className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="login-identifier">Email</Label>
          <Input
            id="login-identifier"
            type="email"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            autoComplete="email"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="login-password">Password</Label>
          <Input
            id="login-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </div>
        {error ? <p className="text-sm font-medium text-red-700">{error}</p> : null}
        <Button type="button" className="w-full bg-slate-950 text-white hover:bg-slate-800" onClick={handleSupabaseLogin} disabled={submitting || !identifier.trim() || !password}>
          <LogIn className="h-4 w-4" />
          {submitting ? "Signing in..." : "Sign in"}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="mock-name">Name</Label>
        <Input
          id="mock-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Your name"
        />
      </div>

      <fieldset className="space-y-3">
        <legend className="text-sm font-medium text-slate-950">Role / title</legend>
        {roleOptions.map((option) => (
          <label
            key={option.role}
            className="flex cursor-pointer gap-3 rounded-md border border-slate-200 bg-white p-4 transition hover:bg-slate-50 has-[:checked]:border-teal-600 has-[:checked]:bg-teal-50"
          >
            <input
              type="radio"
              name="mock-role"
              value={option.role}
              checked={role === option.role}
              onChange={() => setRole(option.role)}
              className="mt-1 h-4 w-4 accent-teal-700"
            />
            <span>
              <span className="block text-sm font-semibold text-slate-950">{option.title}</span>
              <span className="mt-1 block text-sm leading-6 text-slate-600">{option.description}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <Button type="button" className="w-full bg-slate-950 text-white hover:bg-slate-800" onClick={handleContinue}>
        <LogIn className="h-4 w-4" />
        Continue
      </Button>
    </div>
  );
}
