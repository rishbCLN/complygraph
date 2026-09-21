"use client";

import { cn } from "@/lib/format";
import {
  Activity,
  AlertTriangle,
  Boxes,
  BrainCircuit,
  Database,
  FileText,
  ClipboardCheck,
  Gavel,
  GitCompareArrows,
  LayoutDashboard,
  CheckCheck,
  ClipboardList,
  Network,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Store,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/data-map", label: "Data Map", icon: Network },
  { href: "/data-assets", label: "Data Assets", icon: Database },
  { href: "/ai-systems", label: "AI Systems", icon: BrainCircuit },
  { href: "/controls", label: "Controls", icon: ShieldCheck },
  { href: "/control-mappings", label: "Control Mapping", icon: GitCompareArrows },
  { href: "/findings", label: "Findings", icon: AlertTriangle },
  { href: "/risks", label: "Risk Register", icon: ShieldAlert },
  { href: "/approvals", label: "Approvals", icon: CheckCheck },
  { href: "/vendors", label: "Vendors", icon: Store },
  { href: "/regulations", label: "Regulations", icon: Gavel },
  { href: "/ai-investigator", label: "AI Investigator", icon: Sparkles },
  { href: "/self-audit", label: "Self-audit", icon: ClipboardCheck },
  { href: "/campaigns", label: "Audit Campaigns", icon: ClipboardList },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/audit-log", label: "Audit Log", icon: ScrollText },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-panel-2">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <ShieldCheck className="h-5 w-5 text-accent" />
        <span className="text-sm font-semibold">ComplyGraph</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent/15 text-fg"
                  : "text-muted hover:bg-panel hover:text-fg",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3 text-[10px] leading-relaxed text-muted">
        <div className="flex items-center gap-1">
          <Boxes className="h-3 w-3" /> Internal control posture
        </div>
        <p className="mt-1">
          Governance aid only. Not legal advice or certification of compliance.
        </p>
      </div>
    </aside>
  );
}
