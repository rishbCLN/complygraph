"use client";

import { cn } from "@/lib/format";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/ui";

const TABS = [
  { href: "/settings", label: "Organization" },
  { href: "/settings/members", label: "Members" },
  { href: "/settings/connectors", label: "Connectors" },
  { href: "/settings/integrations", label: "Integrations" },
  { href: "/settings/security", label: "Security" },
  { href: "/settings/regulatory", label: "Regulatory" },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <>
      <PageHeader
        title="Settings"
        description="Organization configuration, connectors, and regulatory scope."
      />
      <div className="mb-5 flex items-center gap-1 border-b border-border">
        {TABS.map((t) => {
          const active = pathname === t.href;
          return (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
                active
                  ? "border-accent text-fg"
                  : "border-transparent text-muted hover:text-fg",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
      {children}
    </>
  );
}
