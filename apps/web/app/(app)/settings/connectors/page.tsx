"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { formatDateTime, titleCase } from "@/lib/format";
import { useConnectors, useScanMutation, useScans } from "@/lib/queries";
import { RefreshCw } from "lucide-react";

export default function SettingsConnectorsPage() {
  const connectors = useConnectors();
  const scans = useScans();
  const scanMut = useScanMutation();

  return (
    <div className="space-y-4">
      <Panel title="Connectors">
        {connectors.isLoading ? (
          <Spinner />
        ) : connectors.isError ? (
          <ErrorState message="Could not load connectors." />
        ) : !connectors.data || connectors.data.length === 0 ? (
          <EmptyState message="No connectors configured." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Type</TH>
                <TH>Status</TH>
                <TH>Last Scan</TH>
                <TH></TH>
              </tr>
            </THead>
            <TBodyRows
              rows={connectors.data}
              render={(c) => (
                <tr key={c.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{c.name}</td>
                  <td className="px-4 py-2.5 text-muted">{titleCase(c.type)}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={c.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDateTime(c.last_scan_at)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Button
                      size="sm"
                      onClick={() => scanMut.mutate(c.id)}
                      disabled={scanMut.isPending}
                    >
                      <RefreshCw
                        className={
                          "h-3 w-3 " + (scanMut.isPending ? "animate-spin" : "")
                        }
                      />
                      Scan
                    </Button>
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <Panel title="Recent scans">
        {scans.isLoading ? (
          <Spinner />
        ) : !scans.data || scans.data.length === 0 ? (
          <EmptyState message="No scans have run yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Status</TH>
                <TH>Stage</TH>
                <TH>Items</TH>
                <TH>Findings</TH>
                <TH>Started</TH>
                <TH>Completed</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={scans.data}
              render={(s) => (
                <tr key={s.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5">
                    <Badge
                      label={s.status}
                      variant={
                        s.status === "COMPLETED"
                          ? "PASS"
                          : s.status === "FAILED"
                            ? "FAIL"
                            : "IN_PROGRESS"
                      }
                    />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {titleCase(s.stage) || "—"}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {s.items_scanned}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {s.findings_created}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDateTime(s.created_at)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDateTime(s.completed_at)}
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>
    </div>
  );
}
