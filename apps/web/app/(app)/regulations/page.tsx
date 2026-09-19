"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useRegulations } from "@/lib/queries";
import { useRouter } from "next/navigation";

export default function RegulationsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useRegulations();

  return (
    <>
      <PageHeader
        title="Regulations"
        description="Regulatory frameworks mapped to your control library."
      />
      <Panel title={data ? `${data.length} regulations` : "Regulations"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load regulations." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No regulations configured." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Jurisdiction</TH>
                <TH>Version</TH>
                <TH>Effective</TH>
                <TH>Obligations</TH>
                <TH>Status</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(r) => (
                <tr
                  key={r.id}
                  onClick={() => router.push(`/regulations/${r.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
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
                    <Badge label={r.status} />
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
