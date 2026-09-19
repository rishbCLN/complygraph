"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useProcessingActivities } from "@/lib/queries";

export default function ProcessingActivitiesPage() {
  const { data, isLoading, isError } = useProcessingActivities();

  return (
    <>
      <PageHeader
        title="Processing Activities"
        description="Business-level processing purposes linked to lawful basis, notice, and consent."
      />
      <Panel title={data ? `${data.length} activities` : "Processing Activities"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load processing activities." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No processing activities recorded." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Purpose</TH>
                <TH>Lawful Basis</TH>
                <TH>Owner</TH>
                <TH>Retention</TH>
                <TH>Notice</TH>
                <TH>Consent</TH>
                <TH>Status</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(a) => (
                <tr key={a.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{a.name}</td>
                  <td className="px-4 py-2.5 text-muted">{a.purpose || "—"}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {titleCase(a.lawful_basis)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{a.owner || "—"}</td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {a.retention_period_days
                      ? `${a.retention_period_days}d`
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    {a.has_notice ? (
                      <span className="text-pass">Yes</span>
                    ) : (
                      <span className="text-fail">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {a.has_consent ? (
                      <span className="text-pass">Yes</span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={a.status} />
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
