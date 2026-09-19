"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader, Select } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useFindings } from "@/lib/queries";
import { useRouter } from "next/navigation";
import { useState } from "react";

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const STATUSES = [
  "OPEN",
  "ACKNOWLEDGED",
  "IN_PROGRESS",
  "RESOLVED",
  "ACCEPTED_RISK",
  "FALSE_POSITIVE",
];

export default function FindingsPage() {
  const router = useRouter();
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const { data, isLoading, isError } = useFindings({
    severity: severity || undefined,
    status: status || undefined,
  });

  return (
    <>
      <PageHeader
        title="Findings"
        description="Detected control gaps and governance risks across your data estate."
        actions={
          <div className="flex items-center gap-2">
            <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">All severities</option>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      <Panel
        title={
          data ? `${data.total} finding${data.total === 1 ? "" : "s"}` : "Findings"
        }
      >
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load findings." />
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No findings match these filters." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Severity</TH>
                <TH>Finding</TH>
                <TH>Asset</TH>
                <TH>Control</TH>
                <TH>Owner</TH>
                <TH>Status</TH>
                <TH>Detected</TH>
                <TH>Due</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data.items}
              render={(f) => (
                <tr
                  key={f.id}
                  onClick={() => router.push(`/findings/${f.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5">
                    <Badge label={f.severity} />
                  </td>
                  <td className="px-4 py-2.5 font-medium">{f.title}</td>
                  <td className="px-4 py-2.5 text-muted">{f.asset_name || "—"}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {f.control_code || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{f.owner || "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={f.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(f.detected_at)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{formatDate(f.due_at)}</td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>
    </>
  );
}
