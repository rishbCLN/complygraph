"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { ConfirmDialog, Field, PageHeader, ScoreBar, Skeleton } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/format";
import {
  useFinding,
  useFindingTransition,
  useInvestigateMutation,
  useInvestigations,
} from "@/lib/queries";
import type { Investigation } from "@/lib/types";
import { AlertCircle, CheckCircle2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

const RISK_LABELS: Record<string, string> = {
  sensitivity: "Sensitivity",
  exposure: "Exposure",
  control_gap: "Control gap",
  volume: "Volume",
};

export default function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const finding = useFinding(id);
  const investigations = useInvestigations(id);
  const investigate = useInvestigateMutation();
  const transition = useFindingTransition();
  const [confirm, setConfirm] = useState<null | "resolve" | "accept-risk">(null);

  if (finding.isLoading) {
    return (
      <>
        <PageHeader title="Finding" breadcrumbs={[{ label: "Findings", href: "/findings" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (finding.isError || !finding.data) {
    return (
      <>
        <PageHeader title="Finding" breadcrumbs={[{ label: "Findings", href: "/findings" }]} />
        <ErrorState message="This finding could not be loaded." />
      </>
    );
  }

  const f = finding.data;
  const breakdown = f.risk_breakdown || {};
  const latestInvestigation: Investigation | undefined = investigations.data?.[0];

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: "Findings", href: "/findings" },
          { label: f.title },
        ]}
        title={
          <span className="flex items-center gap-3">
            <Badge label={f.severity} />
            {f.title}
          </span>
        }
        description={<span>Status: <Badge label={f.status} /></span>}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={() => investigate.mutate(id)}
              disabled={investigate.isPending}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {investigate.isPending ? "Investigating…" : "AI Investigate"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setConfirm("resolve")}
              disabled={f.status === "RESOLVED"}
            >
              Resolve
            </Button>
            <Button
              variant="secondary"
              onClick={() => setConfirm("accept-risk")}
              disabled={f.status === "ACCEPTED_RISK"}
            >
              Accept Risk
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Panel title="Why this was detected">
            <div className="p-4 text-sm leading-relaxed text-fg">
              {f.description || "No description recorded."}
            </div>
          </Panel>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Panel title="Affected data">
              <div className="space-y-3 p-4">
                <Field label="Data categories" value={f.data_categories || "—"} />
                <Field
                  label="Asset"
                  value={
                    f.asset_id ? (
                      <Link
                        href={`/data-assets/${f.asset_id}`}
                        className="text-accent hover:underline"
                      >
                        {f.asset_name || f.asset_id}
                      </Link>
                    ) : (
                      "—"
                    )
                  }
                />
              </div>
            </Panel>
            <Panel title="Regulatory / control mapping">
              <div className="space-y-3 p-4">
                <Field
                  label="Control"
                  value={
                    f.control_id ? (
                      <Link
                        href={`/controls/${f.control_id}`}
                        className="text-accent hover:underline"
                      >
                        {f.control_code || f.control_id}
                      </Link>
                    ) : (
                      "—"
                    )
                  }
                />
                <Field label="Source" value={titleCase(f.source)} />
              </div>
            </Panel>
          </div>

          <Panel title="Recommended remediation">
            {f.recommended_actions && f.recommended_actions.length > 0 ? (
              <ul className="space-y-2 p-4">
                {f.recommended_actions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState message="No recommended actions recorded." />
            )}
          </Panel>

          <Panel
            title="AI Investigation"
            actions={
              <span className="text-[10px] uppercase tracking-wider text-muted">
                Advisory only
              </span>
            }
          >
            {investigations.isLoading ? (
              <Spinner />
            ) : !latestInvestigation ? (
              <EmptyState message="No investigation yet. Run AI Investigate to generate an advisory analysis." />
            ) : (
              <InvestigationView inv={latestInvestigation} />
            )}
          </Panel>
        </div>

        <div className="space-y-4">
          <Panel title="Risk calculation">
            <div className="space-y-3 p-4">
              {Object.keys(RISK_LABELS).map((key) => (
                <ScoreBar
                  key={key}
                  label={RISK_LABELS[key]}
                  value={Number(breakdown[key] ?? 0)}
                  max={5}
                />
              ))}
              <div className="mt-4 border-t border-border pt-3">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Overall risk score
                </div>
                <div className="mt-1 text-3xl font-semibold tabular-nums">
                  {f.risk_score}
                  <span className="text-base text-muted"> / 100</span>
                </div>
              </div>
            </div>
          </Panel>

          <Panel title="Details">
            <div className="space-y-3 p-4">
              <Field label="Owner" value={f.owner || "Unassigned"} />
              <Field label="Detected" value={formatDateTime(f.detected_at)} />
              <Field label="Due" value={formatDateTime(f.due_at)} />
              <Field label="Resolved" value={formatDateTime(f.resolved_at)} />
              {f.resolution_note && (
                <Field label="Resolution note" value={f.resolution_note} />
              )}
            </div>
          </Panel>
        </div>
      </div>

      <ConfirmDialog
        open={confirm === "resolve"}
        title="Resolve finding"
        message="Mark this finding as resolved? This will be recorded in the audit log."
        confirmLabel="Resolve"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          transition.mutate({ id, action: "resolve" });
          setConfirm(null);
        }}
      />
      <ConfirmDialog
        open={confirm === "accept-risk"}
        title="Accept risk"
        message="Accept the risk for this finding? Document your justification with the responsible owner. This is recorded in the audit log."
        confirmLabel="Accept Risk"
        danger
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          transition.mutate({ id, action: "accept-risk" });
          setConfirm(null);
        }}
      />
    </>
  );
}

function InvestigationView({ inv }: { inv: Investigation }) {
  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge label={inv.mode} className="bg-upcoming/15 text-upcoming border-upcoming/30" />
        {inv.model && <span className="text-muted">{inv.model}</span>}
        {inv.input_sanitized && (
          <span className="rounded border border-border bg-panel-2 px-2 py-0.5 text-muted">
            {inv.input_sanitized_notice || "AI input sanitized"}
          </span>
        )}
        <span className="rounded border border-border bg-panel-2 px-2 py-0.5 text-muted">
          {inv.raw_pii_excluded_notice || "Raw personal data excluded"}
        </span>
      </div>

      {inv.summary && <p className="text-sm leading-relaxed">{inv.summary}</p>}

      {inv.legal_review_required && (
        <div className="flex items-start gap-2 rounded border border-medium/40 bg-medium/10 px-3 py-2 text-xs text-medium">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          Legal review required before acting on these recommendations.
        </div>
      )}

      {inv.root_causes && inv.root_causes.length > 0 && (
        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted">
            Likely root causes
          </div>
          <div className="space-y-2">
            {inv.root_causes.map((rc, i) => (
              <div key={i} className="rounded border border-border bg-panel-2 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{rc.title}</span>
                  <span className="text-xs text-muted tabular-nums">
                    {Math.round(rc.likelihood * 100)}% likely
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">{rc.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {inv.recommendations && inv.recommendations.length > 0 && (
        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted">
            Recommendations
          </div>
          <div className="space-y-1.5">
            {inv.recommendations.map((r, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <Badge label={r.priority} />
                <span>{r.action}</span>
                {r.requires_human_review && (
                  <span className="text-xs text-medium">(human review)</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {inv.missing_evidence && inv.missing_evidence.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
            Missing evidence
          </div>
          <ul className="list-inside list-disc text-xs text-muted">
            {inv.missing_evidence.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {inv.uncertainty && (
        <div className="text-xs text-muted">
          <span className="font-medium">Uncertainty: </span>
          {inv.uncertainty}
        </div>
      )}
    </div>
  );
}
