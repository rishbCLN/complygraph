"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { ErrorState, EmptyState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Field, PageHeader, Skeleton } from "@/components/ui";
import { formatDateTime, formatNumber, titleCase } from "@/lib/format";
import {
  useDataRequest,
  useDsrTasks,
  useFulfillDsr,
  useMe,
  useVerifyDsr,
} from "@/lib/queries";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function DataRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const req = useDataRequest(id);
  const tasks = useDsrTasks(id);
  const me = useMe();
  const verify = useVerifyDsr();
  const fulfill = useFulfillDsr();
  const [error, setError] = useState<string | null>(null);

  const canManage = me.data?.capabilities?.includes("manage_dsr") ?? false;

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
  const pkg = r.fulfillment;
  const isVerified = r.verification_status === "VERIFIED";
  const isFulfillable = !["GRIEVANCE"].includes(r.request_type);

  async function runVerify() {
    setError(null);
    try {
      await verify.mutateAsync(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed.");
    }
  }

  async function runFulfill() {
    setError(null);
    try {
      await fulfill.mutateAsync(id);
      tasks.refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fulfillment failed.");
    }
  }

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

      {error && (
        <div className="mb-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Request" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-3">
            <Field label="Type" value={titleCase(r.request_type)} />
            <Field label="Status" value={<Badge label={r.status} />} />
            <Field label="Verification" value={<Badge label={r.verification_status} />} />
            <Field label="Received" value={formatDateTime(r.received_at)} />
            <Field label="Due" value={formatDateTime(r.due_at)} />
            <Field label="Fulfilled" value={formatDateTime(r.fulfilled_at)} />
          </div>
          {r.notes && (
            <div className="border-t border-border p-4">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Notes</div>
              <p className="mt-1 text-sm">{r.notes}</p>
            </div>
          )}
        </Panel>

        <Panel title="Fulfillment engine">
          <div className="space-y-3 p-4">
            <p className="text-sm text-muted">
              Verify the requester&apos;s identity, then run the engine to discover and action their
              personal data across managed datastores.
            </p>
            {!isFulfillable && (
              <div className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
                {titleCase(r.request_type)} requests are handled manually and cannot be run through the
                automated engine.
              </div>
            )}
            {canManage ? (
              <div className="flex flex-col gap-2">
                <Button
                  variant="secondary"
                  onClick={runVerify}
                  disabled={isVerified || verify.isPending}
                >
                  {isVerified ? "Identity verified" : verify.isPending ? "Verifying..." : "Verify identity"}
                </Button>
                <Button
                  onClick={runFulfill}
                  disabled={!isVerified || !isFulfillable || fulfill.isPending}
                >
                  {fulfill.isPending ? "Running..." : pkg ? "Re-run fulfillment" : "Fulfill request"}
                </Button>
              </div>
            ) : (
              <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-muted">
                You need the Manage DSR capability to run fulfillment.
              </div>
            )}
          </div>
        </Panel>
      </div>

      {pkg && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Action" value={titleCase(pkg.action)} />
            <MetricCard label="Stores actioned" value={`${pkg.stores_completed}/${pkg.stores_total}`} tone="good" />
            <MetricCard
              label="Manual follow-up"
              value={formatNumber(pkg.stores_skipped)}
              tone={pkg.stores_skipped ? "warn" : "default"}
            />
            <MetricCard label="Records affected" value={formatNumber(pkg.records_affected)} />
          </div>

          <Panel title="Datastore outcomes">
            <Table>
              <THead>
                <tr>
                  <TH>Datastore</TH>
                  <TH>Connector</TH>
                  <TH>Action</TH>
                  <TH>Status</TH>
                  <TH className="text-right">Records</TH>
                  <TH>Personal data fields</TH>
                </tr>
              </THead>
              <TBodyRows
                rows={pkg.stores}
                render={(s, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{s.asset}</td>
                    <td className="px-3 py-2 text-muted">{s.connector_type ?? "Unmanaged"}</td>
                    <td className="px-3 py-2">{titleCase(s.action)}</td>
                    <td className="px-3 py-2"><Badge label={s.status} /></td>
                    <td className="px-3 py-2 text-right">{s.records_affected ?? "-"}</td>
                    <td className="px-3 py-2 text-xs text-muted">
                      {s.fields.length
                        ? s.fields.map((f) => f.name).join(", ")
                        : "None catalogued"}
                    </td>
                  </tr>
                )}
              />
            </Table>
            <p className="border-t border-border px-4 py-2 text-xs text-muted">{pkg.notice}</p>
          </Panel>
        </div>
      )}

      {!pkg && (
        <div className="mt-4">
          <Panel title="Datastore outcomes">
            <EmptyState message="No fulfillment has run yet. Verify identity and run the engine to populate outcomes." />
          </Panel>
        </div>
      )}
    </>
  );
}
