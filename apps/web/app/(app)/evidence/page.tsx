"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import { useEvidence } from "@/lib/queries";

export default function EvidencePage() {
  const { data, isLoading, isError } = useEvidence();

  return (
    <>
      <PageHeader
        title="Evidence"
        description="Evidence lifecycle: collection, freshness, and control linkage."
      />
      <Panel title={data ? `${data.length} evidence items` : "Evidence"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load evidence." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No evidence recorded yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Type</TH>
                <TH>Source</TH>
                <TH>Freshness</TH>
                <TH>Collected</TH>
                <TH>Expires</TH>
                <TH>Owner</TH>
                <TH>Controls</TH>
                <TH>Hash</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(e) => (
                <tr key={e.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{e.name}</td>
                  <td className="px-4 py-2.5 text-muted">{titleCase(e.type)}</td>
                  <td className="px-4 py-2.5 text-muted">{e.source || "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={e.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(e.collected_at)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(e.expires_at)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{e.owner || "—"}</td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {e.linked_controls}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[10px] text-muted">
                    {e.hash ? e.hash.slice(0, 12) : "—"}
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>
    </>
  );
}
