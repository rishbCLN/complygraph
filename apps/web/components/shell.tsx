"use client";

import { cn } from "@/lib/format";
import { setActiveOrg } from "@/lib/api";
import { useAiMode, useLogoutMutation, useMe } from "@/lib/queries";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  Bell,
  Boxes,
  BrainCircuit,
  CheckCheck,
  ClipboardCheck,
  ClipboardList,
  Database,
  FileCheck,
  FileText,
  Gavel,
  GitCompareArrows,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Network,
  Radar,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  useDismissNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from "@/lib/queries";
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
      { href: "/ai-systems", label: "AI Systems", icon: BrainCircuit },
      { href: "/vendors", label: "Vendors", icon: Boxes },
    ],
  },
  {
    label: "Compliance",
    items: [
      { href: "/regulations", label: "Regulations", icon: Gavel },
      { href: "/controls", label: "Controls", icon: ClipboardCheck },
      { href: "/control-mappings", label: "Control Mapping", icon: GitCompareArrows },
      { href: "/findings", label: "Findings", icon: AlertTriangle },
      { href: "/evidence", label: "Evidence", icon: FileText },
      { href: "/campaigns", label: "Audit Campaigns", icon: ClipboardList },
      { href: "/self-audit", label: "Self-audit", icon: BadgeCheck },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/tasks", label: "Tasks", icon: ListChecks },
      { href: "/data-requests", label: "Data Requests", icon: Inbox },
      { href: "/consent", label: "Consent", icon: FileCheck },
      { href: "/risks", label: "Risk Register", icon: Radar },
      { href: "/approvals", label: "Approvals", icon: CheckCheck },
      { href: "/incidents", label: "Incidents", icon: ShieldAlert },
      { href: "/ai-investigator", label: "AI Investigator", icon: Sparkles },
    ],
  },
  {
    label: "Governance",
    items: [
      { href: "/reports", label: "Reports", icon: ScrollText },
      { href: "/notifications", label: "Notifications", icon: Bell },
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

function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data: count } = useUnreadCount();
  const { data: items } = useNotifications();
  const markRead = useMarkNotificationRead();
  const dismiss = useDismissNotification();
  const markAll = useMarkAllNotificationsRead();

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = count?.unread ?? 0;
  const recent = (items ?? []).slice(0, 6);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded p-1.5 text-muted hover:bg-panel-2 hover:text-fg"
        title="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg border border-border bg-panel shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 && (
              <button
                onClick={() => markAll.mutate()}
                className="text-xs text-accent hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {recent.length === 0 ? (
              <div className="px-3 py-6 text-center text-xs text-muted">
                You&apos;re all caught up.
              </div>
            ) : (
              recent.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "border-b border-border/60 px-3 py-2 last:border-0",
                    n.state === "UNREAD" && "bg-panel-2/40",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-medium">{n.title}</span>
                    <span
                      className={cn(
                        "shrink-0 rounded px-1 text-[9px] font-semibold uppercase",
                        n.severity === "CRITICAL"
                          ? "bg-danger/15 text-danger"
                          : n.severity === "WARNING"
                            ? "bg-upcoming/15 text-upcoming"
                            : "bg-muted/15 text-muted",
                      )}
                    >
                      {n.severity}
                    </span>
                  </div>
                  {n.body && <p className="mt-0.5 line-clamp-2 text-[11px] text-muted">{n.body}</p>}
                  <div className="mt-1 flex gap-2">
                    {n.state === "UNREAD" && (
                      <button
                        onClick={() => markRead.mutate(n.id)}
                        className="text-[10px] text-accent hover:underline"
                      >
                        Read
                      </button>
                    )}
                    <button
                      onClick={() => dismiss.mutate(n.id)}
                      className="text-[10px] text-muted hover:underline"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-border px-3 py-2 text-center text-xs text-accent hover:underline"
          >
            View all
          </Link>
        </div>
      )}
    </div>
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
        <NotificationBell />
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
