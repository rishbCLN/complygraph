"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Field, PageHeader, Skeleton } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useObligations, useRegulation } from "@/lib/queries";
import { useParams } from "next/navigation";

export default function RegulationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const regulation = useRegulation(id);
  const obligations = useObligations(id);

  if (regulation.isLoading) {
    return (
      <>
        <PageHeader title="Regulation" breadcrumbs={[{ label: "Regulations", href: "/regulations" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (regulation.isError || !regulation.data) {
    return (
      <>
        <PageHeader title="Regulation" breadcrumbs={[{ label: "Regulations", href: "/regulations" }]} />
        <ErrorState message="This regulation could not be loaded." />
      </>
    );
  }

  const r = regulation.data;

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: "Regulations", href: "/regulations" },
          { label: r.name },
        ]}
        title={r.name}
        description={`${r.jurisdiction}${r.version ? ` · ${r.version}` : ""}`}
        actions={<Badge label={r.status} />}
      />

      <Panel title="Details" className="mb-4">
        <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-4">
          <Field label="Jurisdiction" value={r.jurisdiction} />
          <Field label="Version" value={r.version || "—"} />
          <Field label="Effective from" value={formatDate(r.effective_from)} />
          <Field label="Source" value={r.source_document || "—"} />
        </div>
      </Panel>

      <Panel title={`Obligations (${obligations.data?.length ?? 0})`}>
        {obligations.isLoading ? (
          <Spinner />
        ) : !obligations.data || obligations.data.length === 0 ? (
          <EmptyState message="No obligations recorded for this regulation." />
        ) : (
          <div className="divide-y divide-border">
            {obligations.data.map((o) => (
              <div key={o.id} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted">{o.code}</span>
                    <span className="text-sm font-medium">{o.title}</span>
                  </div>
                  <span className="text-xs text-muted">
                    {o.control_count} control{o.control_count === 1 ? "" : "s"}
                  </span>
                </div>
                {o.description && (
                  <p className="mt-1 text-xs text-muted">{o.description}</p>
                )}
                {o.legal_reference && (
                  <p className="mt-1 text-[11px] text-muted/80">
                    {o.legal_reference}
                    {o.source_section ? ` · ${o.source_section}` : ""}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}
