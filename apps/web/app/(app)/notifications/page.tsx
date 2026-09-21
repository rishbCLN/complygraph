"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, Panel, Spinner } from "@/components/panel";
import { PageHeader, Tabs } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import {
  useDismissNotification,
  useGenerateReminders,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/lib/queries";
import type { Notification } from "@/lib/types";
import Link from "next/link";
import { useState } from "react";

const ENTITY_HREF: Record<string, string> = {
  finding: "/findings",
  task: "/tasks",
  data_request: "/data-requests",
  risk: "/risks",
  control: "/controls",
  evidence: "/evidence",
};

function severityTone(severity: string): "default" | "critical" | "warn" {
  if (severity === "CRITICAL") return "critical";
  if (severity === "WARNING") return "warn";
  return "default";
}

export default function NotificationsPage() {
  const [tab, setTab] = useState("active");
  const stateFilter = tab === "active" ? undefined : tab.toUpperCase();
  const { data, isLoading } = useNotifications(stateFilter);
  const markRead = useMarkNotificationRead();
  const dismiss = useDismissNotification();
  const markAll = useMarkAllNotificationsRead();
  const generate = useGenerateReminders();

  const items = data ?? [];

  function linkFor(n: Notification): string | null {
    if (!n.entity_type || !n.entity_id) return null;
    const base = ENTITY_HREF[n.entity_type];
    if (!base) return null;
    return `${base}/${n.entity_id}`;
  }

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Reminders for expiring evidence, overdue items, and re-assessment outcomes. Generated on a schedule and on demand."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => markAll.mutate()}>
              Mark all read
            </Button>
            <Button
              variant="primary"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
            >
              {generate.isPending ? "Scanning…" : "Run reminders now"}
            </Button>
          </div>
        }
      />

      <Tabs
        tabs={[
          { key: "active", label: "Active" },
          { key: "unread", label: "Unread" },
          { key: "dismissed", label: "Dismissed" },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="mt-4">
        <Panel title={`${items.length} notifications`}>
          {isLoading ? (
            <Spinner />
          ) : items.length === 0 ? (
            <EmptyState message="Nothing here. Run reminders to scan for anything needing attention." />
          ) : (
            <div className="divide-y divide-border">
              {items.map((n) => {
                const href = linkFor(n);
                return (
                  <div
                    key={n.id}
                    className={
                      n.state === "UNREAD"
                        ? "flex items-start justify-between gap-4 bg-panel-2/40 p-4"
                        : "flex items-start justify-between gap-4 p-4"
                    }
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge label={n.severity} variant={severityTone(n.severity)} />
                        <span className="text-sm font-medium">{n.title}</span>
                      </div>
                      {n.body && <p className="mt-1 text-xs text-muted">{n.body}</p>}
                      <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted">
                        <span>{formatDateTime(n.created_at)}</span>
                        {href && (
                          <Link href={href} className="text-accent hover:underline">
                            View
                          </Link>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      {n.state === "UNREAD" && (
                        <Button variant="ghost" onClick={() => markRead.mutate(n.id)}>
                          Mark read
                        </Button>
                      )}
                      {n.state !== "DISMISSED" && (
                        <Button variant="ghost" onClick={() => dismiss.mutate(n.id)}>
                          Dismiss
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
