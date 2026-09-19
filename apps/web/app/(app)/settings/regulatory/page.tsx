"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { formatDate } from "@/lib/format";
import { useRegulations } from "@/lib/queries";

export default function SettingsRegulatoryPage() {
  const regulations = useRegulations();

  return (
    <Panel title="Regulatory scope">
      {regulations.isLoading ? (
        <Spinner />
      ) : regulations.isError ? (
        <ErrorState message="Could not load regulations." />
      ) : !regulations.data || regulations.data.length === 0 ? (
        <EmptyState message="No regulations configured." />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>Regulation</TH>
              <TH>Jurisdiction</TH>
              <TH>Version</TH>
              <TH>Effective</TH>
              <TH>Obligations</TH>
              <TH>Enabled</TH>
              <TH>Status</TH>
            </tr>
          </THead>
          <TBodyRows
            rows={regulations.data}
            render={(r) => (
              <tr key={r.id} className="border-b border-border/60">
                <td className="px-4 py-2.5 font-medium">{r.name}</td>
                <td className="px-4 py-2.5 text-muted">{r.jurisdiction}</td>
                <td className="px-4 py-2.5 text-muted">{r.version || "—"}</td>
                <td className="px-4 py-2.5 text-muted">
                  {formatDate(r.effective_from)}
                </td>
                <td className="px-4 py-2.5 tabular-nums text-muted">
                  {r.obligation_count}
                </td>
                <td className="px-4 py-2.5">
                  {r.enabled ? (
                    <span className="text-pass">Enabled</span>
                  ) : (
                    <span className="text-muted">Disabled</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <Badge label={r.status} />
                </td>
              </tr>
            )}
          />
        </Table>
      )}
    </Panel>
  );
}
