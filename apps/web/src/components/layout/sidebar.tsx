"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BarChart3, Building2, ClipboardList, Home, Layers, LogIn, PlayCircle, ShieldCheck, Users } from "lucide-react";
import { MOCK_USER_STORAGE_KEY, parseMockUser, roleLabels, type MockUserSession } from "@/lib/mock-auth";

export function Sidebar() {
  const [user, setUser] = useState<MockUserSession | null>(null);

  useEffect(() => {
    setUser(parseMockUser(window.localStorage.getItem(MOCK_USER_STORAGE_KEY)));
  }, []);

  const navItems = useMemo(() => {
    if (!user) return [{ title: "Login", href: "/login", icon: LogIn }];
    if (user.role === "platform") {
      return [
        { title: "Platform Dashboard", href: "/platform/dashboard", icon: ShieldCheck },
        { title: "Training Templates", href: "/platform/templates", icon: Layers },
        { title: "Companies", href: "/platform/companies", icon: Building2 },
        { title: "Assignments", href: "/platform/assignments", icon: ClipboardList },
        { title: "Usage / Cost", href: "/platform/usage", icon: BarChart3 },
        { title: "Login", href: "/login", icon: LogIn },
      ];
    }
    if (user.role === "company") {
      return [
        { title: "Company Dashboard", href: "/company/dashboard", icon: Building2 },
        { title: "Assigned Trainings", href: "/company/trainings", icon: Layers },
        { title: "Employees", href: "/company/employees", icon: Users },
        { title: "Reports", href: "/company/reports", icon: ClipboardList },
        { title: "Usage / Cost", href: "/company/usage", icon: BarChart3 },
        { title: "Login", href: "/login", icon: LogIn },
      ];
    }

    return [
      { title: "My Dashboard", href: "/learner/dashboard", icon: Home },
      { title: "My Trainings", href: "/learner/trainings", icon: Layers },
      { title: "Start Demo Session", href: "/learner/session/demo-session-1", icon: PlayCircle },
      { title: "My Report", href: "/learner/report/demo-session-1", icon: ClipboardList },
      { title: "Login", href: "/login", icon: LogIn },
    ];
  }, [user]);

  return (
    <aside className="hidden w-64 shrink-0 lg:block">
      <div className="rounded-lg border border-white/10 bg-[#25214d] p-5 text-white shadow-sm">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-[#18c5b5] p-2 text-[#102b3f]">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">AkademX10 XAI</p>
            <p className="text-xs text-white/60">{user ? roleLabels[user.role] : "Choose an account type"}</p>
          </div>
        </div>
      </div>
      <nav className="mt-4 rounded-lg border border-slate-200 bg-white p-2 shadow-sm">
        {navItems.map(({ title, href, icon: Icon }) => (
          <Link
            key={`${title}-${href}`}
            href={href}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-[#403a70] transition hover:bg-[#eef5ff] hover:text-[#0967e8]"
          >
            <Icon className="h-4 w-4 text-[#0967e8]" />
            {title}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
