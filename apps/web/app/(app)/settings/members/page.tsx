"use client";

import { Badge } from "@/components/badge";
import { EmptyState, Panel, Spinner } from "@/components/panel";
import { Field } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useMe } from "@/lib/queries";

const DEMO_MEMBERS = [
  { email: "admin@asterlane.demo", role: "Admin" },
  { email: "privacy@asterlane.demo", role: "Privacy Officer" },
  { email: "security@asterlane.demo", role: "Security Analyst" },
  { email: "engineer@asterlane.demo", role: "Engineer" },
  { email: "auditor@asterlane.demo", role: "Auditor" },
  { email: "viewer@asterlane.demo", role: "Viewer" },
];

export default function SettingsMembersPage() {
  const me = useMe();

  return (
    <div className="space-y-4">
      <Panel title="Current user">
        {me.isLoading ? (
          <Spinner />
        ) : !me.data ? (
          <EmptyState message="Unable to load your membership." />
        ) : (
          <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-3">
            <Field label="Name" value={me.data.full_name} />
            <Field label="Email" value={me.data.email} />
            <Field label="Role" value={<Badge label={me.data.role} />} />
          </div>
        )}
      </Panel>

      <Panel title="Demo members">
        <div className="border-b border-border bg-panel-2 px-4 py-2 text-xs text-muted">
          Development/demo accounts only. Password: DemoPass123!
        </div>
        <div className="divide-y divide-border">
          {DEMO_MEMBERS.map((m) => (
            <div
              key={m.email}
              className="flex items-center justify-between px-4 py-2.5 text-sm"
            >
              <span className="font-mono text-xs">{m.email}</span>
              <span className="text-muted">{m.role}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
