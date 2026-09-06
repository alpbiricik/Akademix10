"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { LogIn, Menu, PlayCircle, X } from "lucide-react";
import { getRoleNavigationItems } from "@/components/layout/navigation-items";
import { roleDestinations, roleLabels, type AuthenticatedUser } from "@/lib/auth-types";
import { clearStoredSession, getTrustedProfile } from "@/lib/supabase-auth";

export function Topbar() {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    queueMicrotask(() => {
      getTrustedProfile().then(setUser).catch(() => setUser(null));
    });
  }, []);

  function handleLoginClick() {
    if (user) clearStoredSession();
  }

  const navItems = useMemo(() => getRoleNavigationItems(user), [user]);

  useEffect(() => {
    if (!menuOpen) return;

    function handlePointerDown(event: PointerEvent) {
      if (menuRef.current?.contains(event.target as Node)) return;
      setMenuOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  return (
    <header className="border-b border-white/10 bg-[#25214d] text-white shadow-sm">
      <div ref={menuRef} className="relative mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
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
              {item.shortTitle}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {navItems.length ? (
            <button
              type="button"
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-white/15 bg-white/10 text-white shadow-xs transition hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#18c5b5] md:hidden"
              aria-label="Open role navigation menu"
              aria-expanded={menuOpen}
              aria-controls="mobile-role-navigation"
              onClick={() => setMenuOpen((current) => !current)}
            >
              {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          ) : null}
          {user ? (
            <span className="hidden rounded-md bg-white/10 px-2.5 py-1.5 text-xs font-medium text-white/80 sm:inline-flex">
              {roleLabels[user.role]}
            </span>
          ) : null}
          {user?.role === "learner" ? (
            <Link href="/learner/session/active" className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md border border-white/15 bg-white/10 px-2.5 text-sm font-medium text-white shadow-xs transition hover:bg-white/15">
              <PlayCircle className="h-4 w-4" />
              <span className="hidden sm:inline">Training Session</span>
            </Link>
          ) : (

            <Link href={user ? roleDestinations[user.role] : "/login"} className="inline-flex h-8 shrink-0 items-center justify-center rounded-md border border-white/15 bg-white/10 px-2.5 text-sm font-medium text-white shadow-xs transition hover:bg-white/15">
              <span className="hidden sm:inline">{user ? "Workspace" : "Login"}</span>
              <span className="sm:hidden">{user ? "Home" : "Login"}</span>
            </Link>
          )}
          <Link href="/login" onClick={handleLoginClick} className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md bg-[#18c5b5] px-2.5 text-sm font-medium text-[#102b3f] transition hover:bg-[#35d6c6]">
            <LogIn className="h-4 w-4" />
            <span className="hidden sm:inline">{user ? "Logout" : "Login"}</span>
          </Link>
        </div>
        {menuOpen ? (
          <nav
            id="mobile-role-navigation"
            className="absolute left-4 right-4 top-full z-50 mt-2 max-h-[calc(100vh-5rem)] overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 text-[#25214d] shadow-lg md:hidden"
            aria-label="Role navigation"
          >
            {navItems.map(({ title, href, icon: Icon }) => (
              <Link
                key={`${title}-${href}`}
                href={href}
                className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition hover:bg-[#eef5ff] hover:text-[#0967e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0967e8]"
                onClick={() => setMenuOpen(false)}
              >
                <Icon className="h-4 w-4 text-[#0967e8]" />
                {title}
              </Link>
            ))}
          </nav>
        ) : null}
      </div>
    </header>
  );
}
