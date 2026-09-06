import Link from "next/link";
import { ArrowRight, BadgeCheck, BarChart3, Bot, Brain, Clock3, Layers, PlayCircle, Users } from "lucide-react";

const stats = [
  { label: "Learners enabled", value: "200k" },
  { label: "Skill sessions", value: "1,200%" },
  { label: "Completed journeys", value: "2,256" },
  { label: "Client satisfaction", value: "100%" },
];

const previewCards = [
  {
    title: "Roleplay Studio",
    description: "Practice sales, leadership, project, and ethics conversations with guided AI coaching.",
    icon: Brain,
    accent: "bg-[#e62a75]",
  },
  {
    title: "LiveAvatar Lite",
    description: "Controlled avatar moments appear only in high-impact coaching and feedback blocks.",
    icon: Bot,
    accent: "bg-[#18c5b5]",
  },
  {
    title: "Skill Intelligence",
    description: "Reports turn each session into measurable progress across communication skills.",
    icon: BadgeCheck,
    accent: "bg-[#0967e8]",
  },
];

const categories = [
  { title: "Sales Communication", icon: BarChart3, className: "bg-[#e62a75]" },
  { title: "Leadership", icon: Users, className: "bg-[#18c5b5]" },
  { title: "Project Management", icon: Layers, className: "bg-[#0967e8]" },
  { title: "Workplace Ethics", icon: BadgeCheck, className: "bg-[#ff7a1a]" },
];

export default function HomePage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f5f9ff] text-[#25214d]">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
        <Link href="/" className="text-lg font-bold">
          AkademX10 XAI
        </Link>
        <nav className="hidden items-center gap-6 text-sm font-medium text-[#514b7d] md:flex" aria-label="Landing navigation">
          <Link href="/login" className="transition hover:text-[#0967e8]">Login</Link>
          <Link href="/login" className="transition hover:text-[#0967e8]">Choose Role</Link>
          <Link href="/company/dashboard" className="transition hover:text-[#0967e8]">Company</Link>
          <Link href="/platform/dashboard" className="transition hover:text-[#0967e8]">Platform</Link>
        </nav>
      </header>

      <section className="bg-[#25214d]">
          <div className="mx-auto grid max-w-7xl items-start gap-12 px-4 py-12 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8 lg:py-16">
          <div className="py-10 text-white lg:py-16">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#18c5b5]">AI-powered learning platform</p>
            <h1 className="mt-5 max-w-2xl text-5xl font-bold leading-tight sm:text-6xl">
              Upgrade workplace skills with intelligent roleplay.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-white/72">
              AkademX10 XAI helps teams build communication, leadership, project, and ethics skills through guided sessions, scoring, and actionable reporting.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/login" className="inline-flex h-10 shrink-0 items-center justify-center gap-1.5 rounded-md bg-[#ff4f6d] px-4 text-sm font-semibold text-white transition hover:bg-[#ff6b84]">
                Login
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/learner/session/active" className="inline-flex h-10 shrink-0 items-center justify-center gap-1.5 rounded-md bg-white px-4 text-sm font-semibold text-[#25214d] transition hover:bg-[#eef5ff]">
                Start Roleplay Session
                <PlayCircle className="h-4 w-4" />
              </Link>

            </div>
          </div>

          <div className="flex w-full justify-center lg:justify-end">
              <div className="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-2xl shadow-[#1d2d5f]/20">
              <div className="flex items-center justify-between bg-[#0d2f50] px-5 py-3 text-xs text-white/75">
                <span>support@akademx10.ai</span>
                <span>Roleplay Intelligence</span>
              </div>
              <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                <div className="font-bold text-[#25214d]">AkademX10</div>
                <div className="flex gap-4 text-xs font-medium text-slate-500">
                  <span>Dashboard</span>
                  <span>Courses</span>
                  <span>Reports</span>
                </div>
              </div>
              <div className="bg-[#302c5a] px-8 py-10 text-white">
                <div className="grid gap-8 md:grid-cols-[1fr_220px] md:items-center">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#18c5b5]">Over 100 guided sessions available</p>
                    <h2 className="mt-3 text-3xl font-bold">Skill paths for modern teams</h2>
                    <p className="mt-3 text-sm leading-6 text-white/68">
                      Build, assign, run, score, and report training programs from one workspace.
                    </p>
                  </div>
                  <div className="rounded-lg bg-white/10 p-4">
                    <div className="rounded-md bg-[#18c5b5] p-3 text-[#102b3f]">
                      <Bot className="h-8 w-8" />
                      <p className="mt-3 text-sm font-bold">Live coaching blocks</p>
                    </div>
                    <div className="mt-3 rounded-md bg-[#ffb23f] p-3 text-[#392000]">
                      <Clock3 className="h-7 w-7" />
                      <p className="mt-2 text-sm font-bold">40 min · 7 avatar min</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="relative mx-4 -mt-7 grid grid-cols-2 rounded-lg bg-[#203b63] text-white shadow-xl sm:mx-8 lg:grid-cols-4">
                {stats.map((item) => (
                  <div
                    key={item.label}
                    className="min-w-0 border-b border-r border-white/10 px-4 py-5 last:border-r-0 lg:border-b-0"
                    >
                    <p className="text-2xl font-bold">{item.value}</p>
                    <p className="mt-1 text-xs text-white/60">{item.label}</p>
                  </div>
                ))}
              </div>
              <div className="px-4 py-8 sm:px-8 sm:py-10">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  {previewCards.map(({ title, description, icon: Icon, accent }) => (
                    <div key={title} className="rounded-lg border border-slate-100 bg-white p-4 shadow-sm">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-md ${accent} text-white`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <p className="mt-4 font-semibold text-[#25214d]">{title}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#0967e8]">Training categories</p>
          <h2 className="mt-3 text-3xl font-bold">Programs your teams can launch</h2>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {categories.map(({ title, icon: Icon, className }) => (
            <div key={title} className={`${className} rounded-lg p-5 text-white shadow-lg shadow-slate-200`}>
              <Icon className="h-8 w-8" />
              <p className="mt-5 font-semibold">{title}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
