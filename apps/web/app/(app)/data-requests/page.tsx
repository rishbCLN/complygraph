"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import { useDataRequests } from "@/lib/queries";
import { useRouter } from "next/navigation";

export default function DataRequestsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useDataRequests();

  return (
    <>
      <PageHeader
        title="Data Requests"
        description="Data subject requests (access, correction, erasure) and their SLA status."
      />
      <Panel title={data ? `${data.length} requests` : "Data Requests"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load data requests." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No data subject requests." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Requester</TH>
                <TH>Type</TH>
                <TH>Status</TH>
                <TH>Verification</TH>
                <TH>Received</TH>
                <TH>Due</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(r) => (
                <tr
                  key={r.id}
                  onClick={() => router.push(`/data-requests/${r.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5 font-mono text-xs">
                    {r.requester_identifier}
                  </td>
                  <td className="px-4 py-2.5">{titleCase(r.request_type)}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={r.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {titleCase(r.verification_status)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(r.received_at)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(r.due_at)}
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
