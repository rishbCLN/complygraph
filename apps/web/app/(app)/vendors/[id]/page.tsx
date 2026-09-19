"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Field, PageHeader, Skeleton } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useVendor } from "@/lib/queries";
import { useParams } from "next/navigation";

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const vendor = useVendor(id);

  if (vendor.isLoading) {
    return (
      <>
        <PageHeader title="Vendor" breadcrumbs={[{ label: "Vendors", href: "/vendors" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (vendor.isError || !vendor.data) {
    return (
      <>
        <PageHeader title="Vendor" breadcrumbs={[{ label: "Vendors", href: "/vendors" }]} />
        <ErrorState message="This vendor could not be loaded." />
      </>
    );
  }

  const v = vendor.data;

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "Vendors", href: "/vendors" }, { label: v.name }]}
        title={v.name}
        description={v.service_type || "Third-party processor"}
        actions={<Badge label={v.risk_level} variant={v.risk_level} />}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Overview" className="lg:col-span-2">
          <div className="p-4">
            <p className="text-sm leading-relaxed">
              {v.description || "No description recorded."}
            </p>
            <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3">
              <Field label="Country" value={v.country || "—"} />
              <Field label="Contract" value={<Badge label={v.contract_status} />} />
              <Field label="Owner" value={v.owner || "—"} />
              <Field
                label="Data processing"
                value={titleCase(v.data_processing)}
              />
            </div>
          </div>
        </Panel>
        <Panel title="Exposure">
          <div className="space-y-3 p-4">
            <Field
              label="Personal data flows"
              value={
                <span className="text-lg font-semibold tabular-nums">
                  {v.personal_data_flows}
                </span>
              }
            />
            <Field
              label="Open findings"
              value={
                <span
                  className={
                    "text-lg font-semibold tabular-nums " +
                    (v.open_findings > 0 ? "text-medium" : "text-pass")
                  }
                >
                  {v.open_findings}
                </span>
              }
            />
          </div>
        </Panel>
      </div>
    </>
  );
}
