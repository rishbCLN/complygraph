"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Field, PageHeader, ScoreBar, Skeleton } from "@/components/ui";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { formatDate, formatDateTime, titleCase } from "@/lib/format";
import {
  useAssessControlMutation,
  useControl,
  useControlAssessment,
  useControlEvidence,
  useControlMappings,
  useReusableEvidence,
} from "@/lib/queries";
import { CalendarClock } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function ControlDetailPage() {
  const { id } = useParams<{ id: string }>();
  const control = useControl(id);
  const assessment = useControlAssessment(id);
  const evidence = useControlEvidence(id);
  const mappings = useControlMappings(id);
  const reusable = useReusableEvidence(id);
  const assess = useAssessControlMutation();

  if (control.isLoading) {
    return (
      <>
        <PageHeader title="Control" breadcrumbs={[{ label: "Controls", href: "/controls" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (control.isError || !control.data) {
    return (
      <>
        <PageHeader title="Control" breadcrumbs={[{ label: "Controls", href: "/controls" }]} />
        <ErrorState message="This control could not be loaded." />
      </>
    );
  }

  const c = control.data;
  const isUpcoming = c.temporal_status === "upcoming";
  const a = assessment.data;

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "Controls", href: "/controls" }, { label: c.code }]}
        title={
          <span className="flex items-center gap-3">
            <span className="font-mono text-base text-muted">{c.code}</span>
            {c.title}
          </span>
        }
        description={titleCase(c.category)}
        actions={
          !isUpcoming && (
            <Button
              variant="primary"
              onClick={() => assess.mutate(id)}
              disabled={assess.isPending}
            >
              {assess.isPending ? "Assessing…" : "Re-assess"}
            </Button>
          )
        }
      />

      {isUpcoming && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-upcoming/40 bg-upcoming/10 px-4 py-3 text-sm text-upcoming">
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">
              UPCOMING — Effective {formatDate(c.effective_from)}
            </div>
            <div className="mt-0.5 text-xs text-upcoming/80">
              This control is displayed for preparation, not as a currently failed
              control.
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Panel title="Description">
            <div className="p-4 text-sm leading-relaxed">
              {c.description || "No description recorded."}
            </div>
          </Panel>

          <Panel
            title="Assessment"
            actions={
              a && (
                <span className="text-xs text-muted">
                  {a.automated ? "Automated" : "Manual"} ·{" "}
                  {formatDate(a.assessment_date)}
                </span>
              )
            }
          >
            {assessment.isLoading ? (
              <Spinner />
            ) : isUpcoming ? (
              <EmptyState message="Assessment deferred until the control is in force." />
            ) : !a ? (
              <EmptyState message="Not yet assessed. Run an assessment to evaluate this control." />
            ) : (
              <div className="space-y-3 p-4">
                <div className="flex items-center gap-3">
                  <Badge label={a.status} />
                  <span className="text-sm tabular-nums text-muted">
                    Score {a.score}
                  </span>
                </div>
                <ScoreBar label="Score" value={a.score} max={100} />
                {a.reason && (
                  <p className="text-sm text-muted">{a.reason}</p>
                )}
                <div className="text-xs text-muted">
                  {a.evidence_count} linked evidence item
                  {a.evidence_count === 1 ? "" : "s"}
                </div>
              </div>
            )}
          </Panel>

          <Panel title="Evidence">
            {evidence.isLoading ? (
              <Spinner />
            ) : !evidence.data || evidence.data.length === 0 ? (
              <EmptyState message="No evidence linked to this control." />
            ) : (
              <Table>
                <THead>
                  <tr>
                    <TH>Name</TH>
                    <TH>Type</TH>
                    <TH>Relation</TH>
                    <TH>Freshness</TH>
                    <TH>Collected</TH>
                    <TH>Expires</TH>
                  </tr>
                </THead>
                <TBodyRows
                  rows={evidence.data}
                  render={(e) => (
                    <tr key={e.id} className="border-b border-border/60">
                      <td className="px-4 py-2.5">{e.name}</td>
                      <td className="px-4 py-2.5 text-muted">
                        {titleCase(e.type)}
                      </td>
                      <td className="px-4 py-2.5 text-muted">
                        {titleCase(e.relation_type)}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge label={e.status} />
                      </td>
                      <td className="px-4 py-2.5 text-muted">
                        {formatDate(e.collected_at)}
                      </td>
                      <td className="px-4 py-2.5 text-muted">
                        {formatDate(e.expires_at)}
                      </td>
                    </tr>
                  )}
                />
              </Table>
            )}
          </Panel>

          <Panel
            title="Cross-framework mappings"
            actions={
              <Link
                href="/control-mappings"
                className="text-xs text-accent hover:underline"
              >
                Mapping explorer
              </Link>
            }
          >
            {mappings.isLoading ? (
              <Spinner />
            ) : !mappings.data || mappings.data.length === 0 ? (
              <EmptyState message="No controls in other frameworks are mapped to this control." />
            ) : (
              <Table>
                <THead>
                  <tr>
                    <TH>Direction</TH>
                    <TH>Control</TH>
                    <TH>Framework</TH>
                    <TH>Relation</TH>
                    <TH>Confidence</TH>
                  </tr>
                </THead>
                <TBodyRows
                  rows={mappings.data}
                  render={(m) => (
                    <tr key={m.id} className="border-b border-border/60">
                      <td className="px-4 py-2.5 text-muted">
                        {m.direction === "outgoing" ? "→ maps to" : "← mapped by"}
                      </td>
                      <td className="px-4 py-2.5">
                        <Link
                          href={`/controls/${m.other.id}`}
                          className="font-mono text-xs text-accent hover:underline"
                        >
                          {m.other.code}
                        </Link>
                        <div className="text-xs text-muted">{m.other.title}</div>
                      </td>
                      <td className="px-4 py-2.5 text-muted">
                        {m.other.regulation_name || "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge label={m.relation_type} />
                      </td>
                      <td className="px-4 py-2.5 tabular-nums text-muted">
                        {Math.round(m.confidence * 100)}%
                      </td>
                    </tr>
                  )}
                />
              </Table>
            )}
          </Panel>

          {reusable.data && reusable.data.length > 0 && (
            <Panel title="Reusable evidence (review required)">
              <div className="border-b border-border/60 px-4 py-2.5 text-xs text-muted">
                Evidence collected for mapped controls that may help satisfy this
                control. Human review is required before it counts here — it is not
                applied automatically.
              </div>
              <Table>
                <THead>
                  <tr>
                    <TH>Evidence</TH>
                    <TH>From control</TH>
                    <TH>Via relation</TH>
                    <TH>Freshness</TH>
                  </tr>
                </THead>
                <TBodyRows
                  rows={reusable.data}
                  render={(r) => (
                    <tr key={r.via_mapping_id + r.evidence_id} className="border-b border-border/60">
                      <td className="px-4 py-2.5">
                        {r.evidence_name}
                        <div className="text-xs text-muted">
                          {titleCase(r.evidence_type)}
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        <Link
                          href={`/controls/${r.source_control.id}`}
                          className="font-mono text-xs text-accent hover:underline"
                        >
                          {r.source_control.code}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge label={r.mapping_relation} />
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge label={r.status} />
                      </td>
                    </tr>
                  )}
                />
              </Table>
            </Panel>
          )}
        </div>

        <div className="space-y-4">
          <Panel title="Reference">
            <div className="space-y-3 p-4">
              <Field label="Legal reference" value={c.legal_reference || "—"} />
              <Field label="Source section" value={c.source_section || "—"} />
              <Field label="Regulation" value={c.regulation_name || "—"} />
              <Field label="Effective from" value={formatDate(c.effective_from)} />
              <Field
                label="Temporal status"
                value={<Badge label={c.temporal_status} />}
              />
              <Field
                label="Default severity"
                value={<Badge label={c.severity_default} />}
              />
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
