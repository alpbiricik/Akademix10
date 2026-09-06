import type { LucideIcon } from "lucide-react";
import { BarChart3, Building2, ClipboardList, Home, Layers, LogIn, PlayCircle, ShieldCheck, Users } from "lucide-react";
import type { AuthenticatedUser, UserRole } from "@/lib/auth-types";

export interface RoleNavigationItem {
  title: string;
  shortTitle: string;
  href: string;
  icon: LucideIcon;
}

const roleNavigation: Record<UserRole, RoleNavigationItem[]> = {
  platform: [
    { title: "Platform Dashboard", shortTitle: "Platform", href: "/platform/dashboard", icon: ShieldCheck },
    { title: "Training Templates", shortTitle: "Templates", href: "/platform/templates", icon: Layers },
    { title: "Companies", shortTitle: "Companies", href: "/platform/companies", icon: Building2 },
    { title: "Assignments", shortTitle: "Assignments", href: "/platform/assignments", icon: ClipboardList },
    { title: "Reports", shortTitle: "Reports", href: "/platform/reports", icon: ClipboardList },
    { title: "Usage / Cost", shortTitle: "Usage", href: "/platform/usage", icon: BarChart3 },
  ],
  company: [
    { title: "Company Dashboard", shortTitle: "Company", href: "/company/dashboard", icon: Building2 },
    { title: "Assigned Trainings", shortTitle: "Trainings", href: "/company/trainings", icon: Layers },
    { title: "Employees", shortTitle: "Employees", href: "/company/employees", icon: Users },
    { title: "Reports", shortTitle: "Reports", href: "/company/reports", icon: ClipboardList },
    { title: "Usage / Cost", shortTitle: "Usage", href: "/company/usage", icon: BarChart3 },
  ],
  learner: [
    { title: "My Dashboard", shortTitle: "Dashboard", href: "/learner/dashboard", icon: Home },
    { title: "My Trainings", shortTitle: "Trainings", href: "/learner/trainings", icon: Layers },
    { title: "Training Session", shortTitle: "Session", href: "/learner/session/active", icon: PlayCircle },
    { title: "My Report", shortTitle: "Report", href: "/learner/sessions/active/report", icon: ClipboardList },
  ],

};

const loginItem: RoleNavigationItem = { title: "Login", shortTitle: "Login", href: "/login", icon: LogIn };

export function getRoleNavigationItems(user: AuthenticatedUser | null, includeLogin = false): RoleNavigationItem[] {
  const items = user ? roleNavigation[user.role] : [];
  return includeLogin ? [...items, loginItem] : items;
}

export function getLoginNavigationItem() {
  return loginItem;
}
