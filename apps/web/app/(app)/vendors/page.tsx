"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useVendors } from "@/lib/queries";
import { useRouter } from "next/navigation";

export default function VendorsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useVendors();

  return (
    <>
      <PageHeader
        title="Vendors"
        description="Third-party processors and the personal data flowing to them."
      />
      <Panel title={data ? `${data.length} vendors` : "Vendors"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load vendors." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No vendors recorded." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Vendor</TH>
                <TH>Service</TH>
                <TH>Country</TH>
                <TH>Contract</TH>
                <TH>Risk</TH>
                <TH>PII Flows</TH>
                <TH>Open Findings</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(v) => (
                <tr
                  key={v.id}
                  onClick={() => router.push(`/vendors/${v.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5 font-medium">{v.name}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {v.service_type || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{v.country || "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={v.contract_status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={v.risk_level} variant={v.risk_level} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {v.personal_data_flows}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {v.open_findings}
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
