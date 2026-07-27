"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { LogIn, PlayCircle } from "lucide-react";
import { MOCK_USER_STORAGE_KEY, parseMockUser, roleDestinations, roleLabels, type MockUserSession } from "@/lib/mock-auth";

export function Topbar() {
  const [user, setUser] = useState<MockUserSession | null>(null);

  useEffect(() => {
    setUser(parseMockUser(window.localStorage.getItem(MOCK_USER_STORAGE_KEY)));
  }, []);

  const navItems = useMemo(() => {
    if (!user) return [];
    if (user.role === "platform") {
      return [
        { title: "Platform", href: "/platform/dashboard" },
        { title: "Templates", href: "/platform/templates" },
        { title: "Companies", href: "/platform/companies" },
        { title: "Usage", href: "/platform/usage" },
      ];
    }
    if (user.role === "company") {
      return [
        { title: "Company", href: "/company/dashboard" },
        { title: "Trainings", href: "/company/trainings" },
        { title: "Employees", href: "/company/employees" },
        { title: "Reports", href: "/company/reports" },
      ];
    }

    return [
      { title: "Dashboard", href: "/learner/dashboard" },
      { title: "Trainings", href: "/learner/trainings" },
      { title: "Demo Session", href: "/learner/session/demo-session-1" },
      { title: "Report", href: "/learner/report/demo-session-1" },
    ];
  }, [user]);

  return (
    <header className="border-b border-white/10 bg-[#25214d] text-white shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="text-sm font-semibold text-white">
          AkademX10 XAI
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link
              key={`${item.title}-${item.href}`}
              href={item.href}
              className="rounded-md px-2.5 py-1.5 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white"
            >
              {item.title}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {user ? (
            <span className="hidden rounded-md bg-white/10 px-2.5 py-1.5 text-xs font-medium text-white/80 sm:inline-flex">
              {roleLabels[user.role]}
            </span>
          ) : null}
          {user?.role === "learner" ? (
            <Link href="/learner/session/demo-session-1" className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md border border-white/15 bg-white/10 px-2.5 text-sm font-medium text-white shadow-xs transition hover:bg-white/15">
              <PlayCircle className="h-4 w-4" />
              Demo Session
            </Link>
          ) : (
            <Link href={user ? roleDestinations[user.role] : "/login"} className="inline-flex h-8 shrink-0 items-center justify-center rounded-md border border-white/15 bg-white/10 px-2.5 text-sm font-medium text-white shadow-xs transition hover:bg-white/15">
              {user ? "Workspace" : "Choose Role"}
            </Link>
          )}
          <Link href="/login" className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md bg-[#18c5b5] px-2.5 text-sm font-medium text-[#102b3f] transition hover:bg-[#35d6c6]">
            <LogIn className="h-4 w-4" />
            Login
          </Link>
        </div>
      </div>
    </header>
  );
}
