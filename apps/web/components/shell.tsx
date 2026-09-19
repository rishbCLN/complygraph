"use client";

import { cn } from "@/lib/format";
import { setActiveOrg } from "@/lib/api";
import { useAiMode, useLogoutMutation, useMe } from "@/lib/queries";
import {
  Activity,
  AlertTriangle,
  Boxes,
  ClipboardCheck,
  Database,
  FileText,
  Gavel,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Network,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { GlobalSearch } from "./global-search";

type NavItem = { href: string; label: string; icon: typeof Database };
type NavGroup = { label: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Inventory",
    items: [
      { href: "/data-assets", label: "Data Assets", icon: Database },
      { href: "/data-map", label: "Data Map", icon: Network },
      { href: "/processing-activities", label: "Processing", icon: Workflow },
      { href: "/vendors", label: "Vendors", icon: Boxes },
    ],
  },
  {
    label: "Compliance",
    items: [
      { href: "/regulations", label: "Regulations", icon: Gavel },
      { href: "/controls", label: "Controls", icon: ClipboardCheck },
      { href: "/findings", label: "Findings", icon: AlertTriangle },
      { href: "/evidence", label: "Evidence", icon: FileText },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/tasks", label: "Tasks", icon: ListChecks },
      { href: "/data-requests", label: "Data Requests", icon: Inbox },
      { href: "/incidents", label: "Incidents", icon: ShieldAlert },
      { href: "/ai-investigator", label: "AI Investigator", icon: Sparkles },
    ],
  },
  {
    label: "Governance",
    items: [
      { href: "/reports", label: "Reports", icon: ScrollText },
      { href: "/audit-log", label: "Audit Log", icon: Activity },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-panel-2">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <ShieldCheck className="h-5 w-5 text-accent" />
        <span className="text-sm font-semibold tracking-tight">ComplyGraph</span>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV.map((group) => (
          <div key={group.label} className="mb-4">
            <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted/70">
              {group.label}
            </div>
            {group.items.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(item.href + "/");
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded px-2 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-accent-2/15 text-fg"
                      : "text-muted hover:bg-panel hover:text-fg",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      active ? "text-accent" : "text-muted",
                    )}
                  />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

function Topbar({ orgName, userName }: { orgName: string; userName: string }) {
  const router = useRouter();
  const logout = useLogoutMutation();
  const { data: aiMode } = useAiMode();

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      // ignore — clear local state regardless
    }
    setActiveOrg(null);
    router.push("/login");
  }

  const aiLabel =
    aiMode?.ai_mode === "live"
      ? "AI: Live"
      : aiMode?.ai_mode === "deterministic"
        ? "AI: Deterministic"
        : "AI: Advisory";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-panel px-4">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold">{orgName}</span>
      </div>
      <div className="flex items-center gap-3">
        <GlobalSearch />
        <span
          className="rounded border border-border bg-panel-2 px-2 py-1 text-xs text-muted"
          title="AI is advisory only. The deterministic engine makes decisions."
        >
          {aiLabel}
        </span>
        <div className="flex items-center gap-2 border-l border-border pl-3">
          <div className="text-right">
            <div className="text-xs font-medium">{userName}</div>
          </div>
          <button
            onClick={handleLogout}
            className="rounded p-1.5 text-muted hover:bg-panel-2 hover:text-fg"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { data: me, isLoading, isError, error } = useMe();

  useEffect(() => {
    if (isError) {
      const status = (error as { status?: number } | null)?.status;
      if (status === 401 || status === 403 || status === undefined) {
        router.replace("/login");
      }
    }
  }, [isError, error, router]);

  useEffect(() => {
    if (me?.organization?.id) setActiveOrg(me.organization.id);
  }, [me]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" />
        Loading workspace…
      </div>
    );
  }

  if (isError || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Redirecting to sign in…
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar orgName={me.organization.name} userName={me.full_name} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] px-6 py-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
