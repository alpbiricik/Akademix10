"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MOCK_USER_STORAGE_KEY, type MockRole } from "@/lib/mock-auth";

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
