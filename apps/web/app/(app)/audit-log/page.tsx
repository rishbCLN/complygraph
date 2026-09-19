"use client";

import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Button } from "@/components/button";
import { PageHeader } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAuditEvents } from "@/lib/queries";
import { useState } from "react";

export default function AuditLogPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useAuditEvents(page);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader
        title="Audit Log"
        description="Immutable record of governance-relevant actions across the platform."
      />
      <Panel
        title={data ? `${data.total} events` : "Audit Log"}
        actions={
          data && (
            <div className="flex items-center gap-2 text-xs text-muted">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                Prev
              </Button>
              <span>
                Page {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                Next
              </Button>
            </div>
          )
        }
      >
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load the audit log." />
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No audit events recorded." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Timestamp</TH>
                <TH>Action</TH>
                <TH>Entity</TH>
                <TH>Metadata</TH>
                <TH>IP</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data.items}
              render={(e) => (
                <tr key={e.id} className="border-b border-border/60 align-top">
                  <td className="whitespace-nowrap px-4 py-2.5 text-muted">
                    {formatDateTime(e.created_at)}
                  </td>
                  <td className="px-4 py-2.5 font-medium">
                    {titleCase(e.action)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {e.entity_type ? (
                      <span>
                        {titleCase(e.entity_type)}
                        {e.entity_id && (
                          <span className="ml-1 font-mono text-[10px] text-muted/70">
                            {e.entity_id.slice(0, 8)}
                          </span>
                        )}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[10px] text-muted">
                    {e.metadata && Object.keys(e.metadata).length > 0
                      ? JSON.stringify(e.metadata)
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {e.ip_address || "—"}
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
