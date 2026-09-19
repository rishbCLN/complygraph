"use client";

import { Badge } from "@/components/badge";
import { ErrorState, Panel, Spinner } from "@/components/panel";
import { Field, PageHeader, Skeleton } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/format";
import { useDataRequest } from "@/lib/queries";
import { useParams } from "next/navigation";

export default function DataRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const req = useDataRequest(id);

  if (req.isLoading) {
    return (
      <>
        <PageHeader title="Data Request" breadcrumbs={[{ label: "Data Requests", href: "/data-requests" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (req.isError || !req.data) {
    return (
      <>
        <PageHeader title="Data Request" breadcrumbs={[{ label: "Data Requests", href: "/data-requests" }]} />
        <ErrorState message="This data request could not be loaded." />
      </>
    );
  }

  const r = req.data;

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: "Data Requests", href: "/data-requests" },
          { label: r.requester_identifier },
        ]}
        title={titleCase(r.request_type)}
        description={r.requester_identifier}
        actions={<Badge label={r.status} />}
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Request" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-3">
            <Field label="Type" value={titleCase(r.request_type)} />
            <Field label="Status" value={<Badge label={r.status} />} />
            <Field
              label="Verification"
              value={titleCase(r.verification_status)}
            />
            <Field label="Received" value={formatDateTime(r.received_at)} />
            <Field label="Due" value={formatDateTime(r.due_at)} />
            <Field label="Completed" value={formatDateTime(r.completed_at)} />
          </div>
          {r.notes && (
            <div className="border-t border-border p-4">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                Notes
              </div>
              <p className="mt-1 text-sm">{r.notes}</p>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
