"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Field, PageHeader, Skeleton } from "@/components/ui";
import { formatDateTime, formatNumber } from "@/lib/format";
import { useIncident } from "@/lib/queries";
import { useParams } from "next/navigation";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const incident = useIncident(id);

  if (incident.isLoading) {
    return (
      <>
        <PageHeader title="Incident" breadcrumbs={[{ label: "Incidents", href: "/incidents" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (incident.isError || !incident.data) {
    return (
      <>
        <PageHeader title="Incident" breadcrumbs={[{ label: "Incidents", href: "/incidents" }]} />
        <ErrorState message="This incident could not be loaded." />
      </>
    );
  }

  const i = incident.data;
  const events = i.timeline?.events || [];

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "Incidents", href: "/incidents" }, { label: i.title }]}
        title={
          <span className="flex items-center gap-3">
            <Badge label={i.severity} />
            {i.title}
          </span>
        }
        description={<Badge label={i.status} />}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Panel title="Overview">
            <div className="p-4">
              <p className="text-sm leading-relaxed">
                {i.description || "No description recorded."}
              </p>
              <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3">
                <Field label="Detected" value={formatDateTime(i.detected_at)} />
                <Field label="Contained" value={formatDateTime(i.contained_at)} />
                <Field
                  label="Affected records"
                  value={formatNumber(i.affected_records_estimate)}
                />
              </div>
            </div>
          </Panel>

          {(i.root_cause || i.remediation) && (
            <Panel title="Analysis">
              <div className="space-y-3 p-4">
                {i.root_cause && (
                  <Field label="Root cause" value={i.root_cause} />
                )}
                {i.remediation && (
                  <Field label="Remediation" value={i.remediation} />
                )}
              </div>
            </Panel>
          )}

          <Panel title="Timeline">
            {events.length === 0 ? (
              <EmptyState message="No timeline events yet." />
            ) : (
              <ol className="relative space-y-4 p-4 pl-8">
                {events.map((e, idx) => (
                  <li key={idx} className="relative">
                    <span className="absolute -left-6 top-1 h-2 w-2 rounded-full bg-accent" />
                    <div className="text-xs text-muted">
                      {formatDateTime(e.at)}
                    </div>
                    <div className="text-sm">{e.event}</div>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </div>

        <div className="space-y-4">
          <Panel title="Notifications">
            <div className="space-y-3 p-4">
              <Field
                label="Data Protection Board"
                value={i.board_notification_status.replace(/_/g, " ")}
              />
              <Field
                label="Affected principals"
                value={i.principal_notification_status.replace(/_/g, " ")}
              />
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
