"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { formatDate, formatNumber } from "@/lib/format";
import { useIncidents } from "@/lib/queries";
import { useRouter } from "next/navigation";

export default function IncidentsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useIncidents();

  return (
    <>
      <PageHeader
        title="Incidents"
        description="Breach incidents, containment status, and notification tracking."
      />
      <Panel title={data ? `${data.length} incidents` : "Incidents"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load incidents." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No breach incidents recorded." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Incident</TH>
                <TH>Severity</TH>
                <TH>Status</TH>
                <TH>Detected</TH>
                <TH>Affected Records</TH>
                <TH>Board</TH>
                <TH>Principals</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(i) => (
                <tr
                  key={i.id}
                  onClick={() => router.push(`/incidents/${i.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5 font-medium">{i.title}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={i.severity} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={i.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(i.detected_at)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {formatNumber(i.affected_records_estimate)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {i.board_notification_status.replace(/_/g, " ")}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {i.principal_notification_status.replace(/_/g, " ")}
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
