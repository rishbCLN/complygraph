"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { downloadUrl } from "@/lib/api";
import { cn, formatDateTime, titleCase } from "@/lib/format";
import {
  useAiSystem,
  useAiSystemComponents,
  useAiSystemFlows,
  useAnalyzeSystemMutation,
} from "@/lib/queries";
import type {
  AnalysisReport,
  ChangeImpact,
  FactProvenance,
} from "@/lib/types";
import {
  ArrowRight,
  Download,
  GitCompareArrows,
  PlayCircle,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

// A control's status ranked by attention (worse first).
const STATUS_ORDER: Record<string, number> = {
  FAIL: 0,
  NO_EVIDENCE: 1,
  NEEDS_REVIEW: 2,
  PARTIAL: 3,
  UPCOMING: 4,
  PASS: 5,
  NOT_APPLICABLE: 6,
};

const CONFIDENCE_STYLE: Record<string, string> = {
  DECLARED: "bg-pass/15 text-pass border-pass/30",
  OBSERVED: "bg-pass/15 text-pass border-pass/30",
  INFERRED: "bg-medium/15 text-medium border-medium/30",
  UNKNOWN: "bg-muted/10 text-muted border-border",
};

function ProvenanceBadge({ p }: { p: FactProvenance }) {
  return (
    <span
      title={p.basis}
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium tracking-wide",
        CONFIDENCE_STYLE[p.confidence] || "bg-muted/10 text-muted border-border",
      )}
    >
      {titleCase(p.confidence)}
    </span>
  );
}

// Facts worth surfacing in the report, in a stable, human-friendly order.
const FACT_KEYS: { key: string; label: string }[] = [
  { key: "sector", label: "Sector" },
  { key: "system_type", label: "System type" },
  { key: "lifecycle_stage", label: "Lifecycle stage" },
  { key: "is_reviewed", label: "Reviewed" },
  { key: "processes_personal_data", label: "Processes personal data" },
  { key: "makes_automated_decisions", label: "Automated decisions" },
  { key: "high_risk", label: "High risk" },
  { key: "has_vendors", label: "Uses vendors" },
  { key: "has_external_inference", label: "External inference" },
  { key: "has_cross_border_flow", label: "Cross-border flow" },
  { key: "non_india_regions", label: "Non-India regions" },
];

function factValue(v: unknown): string {
  if (v === true) return "Yes";
  if (v === false) return "No";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "None";
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function ChangeImpactPanel({ changes }: { changes: ChangeImpact }) {
  if (changes.is_baseline) {
    return (
      <Panel
        title={
          <span className="flex items-center gap-2">
            <GitCompareArrows className="h-4 w-4 text-muted" />
            Change impact
          </span>
        }
      >
        <EmptyState message="Baseline run — no previous snapshot to compare against yet. Re-analyze after a change to see drift." />
      </Panel>
    );
  }
  const nothing =
    changes.regressed.length === 0 &&
    changes.improved.length === 0 &&
    changes.added.length === 0 &&
    changes.removed.length === 0;
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <GitCompareArrows className="h-4 w-4 text-muted" />
          Change impact
        </span>
      }
      actions={
        changes.previous_at && (
          <span className="text-xs text-muted">
            vs {formatDateTime(changes.previous_at)}
          </span>
        )
      }
    >
      <div className="space-y-4 p-4">
        {nothing && (
          <p className="text-sm text-muted">
            No control status changed since the previous snapshot (
            {changes.unchanged} unchanged).
          </p>
        )}
        {changes.regressed.length > 0 && (
          <div>
            <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-fail">
              Regressed ({changes.regressed.length})
            </div>
            <div className="space-y-1.5">
              {changes.regressed.map((t) => (
                <div key={t.code} className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-xs">{t.code}</span>
                  <Badge label={t.from} />
                  <ArrowRight className="h-3 w-3 text-muted" />
                  <Badge label={t.to} />
                </div>
              ))}
            </div>
          </div>
        )}
        {changes.improved.length > 0 && (
          <div>
            <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-pass">
              Improved ({changes.improved.length})
            </div>
            <div className="space-y-1.5">
              {changes.improved.map((t) => (
                <div key={t.code} className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-xs">{t.code}</span>
                  <Badge label={t.from} />
                  <ArrowRight className="h-3 w-3 text-muted" />
                  <Badge label={t.to} />
                </div>
              ))}
            </div>
          </div>
        )}
        {(changes.added.length > 0 || changes.removed.length > 0) && (
          <div className="text-xs text-muted">
            {changes.added.length} control(s) newly in scope, {changes.removed.length}{" "}
            no longer in scope.
          </div>
        )}
      </div>
    </Panel>
  );
}

export default function AiSystemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const system = useAiSystem(id);
  const components = useAiSystemComponents(id);
  const flows = useAiSystemFlows(id);
  const analyze = useAnalyzeSystemMutation();
  const [tab, setTab] = useState("analysis");

  const report: AnalysisReport | undefined = analyze.data;

  if (system.isLoading) {
    return (
      <>
        <PageHeader
          title="AI System"
          breadcrumbs={[{ label: "AI Systems", href: "/ai-systems" }]}
        />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (system.isError || !system.data) {
    return (
      <>
        <PageHeader
          title="AI System"
          breadcrumbs={[{ label: "AI Systems", href: "/ai-systems" }]}
        />
        <ErrorState message="This AI system could not be loaded." />
      </>
    );
  }

  const s = system.data;
  const sortedControls = report
    ? [...report.controls].sort(
        (a, b) =>
          (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9) ||
          a.code.localeCompare(b.code),
      )
    : [];

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "AI Systems", href: "/ai-systems" }, { label: s.name }]}
        title={s.name}
        description={s.business_purpose || s.description || titleCase(s.system_type)}
        actions={
          <div className="flex items-center gap-2">
            <a
              href={downloadUrl(`/reports/system/${s.id}/pdf`)}
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary">
                <Download className="h-4 w-4" />
                Report PDF
              </Button>
            </a>
            <Button
              variant="primary"
              onClick={() => analyze.mutate(id)}
              disabled={analyze.isPending}
            >
              <PlayCircle className="h-4 w-4" />
              {analyze.isPending ? "Analyzing…" : "Analyze"}
            </Button>
          </div>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-3 rounded-lg border border-border bg-panel px-4 py-3 md:grid-cols-4 lg:grid-cols-6">
        <Field label="Sector" value={<span className="uppercase">{s.sector}</span>} />
        <Field label="Type" value={s.system_type} />
        <Field label="Stage" value={<Badge label={s.lifecycle_stage} />} />
        <Field label="Review" value={<Badge label={s.review_status} />} />
        <Field label="Owner" value={s.owner || "—"} />
        <Field
          label="Risk"
          value={s.high_risk ? <Badge label="HIGH_RISK" /> : "Standard"}
        />
      </div>

      <Tabs
        tabs={[
          { key: "analysis", label: "Analysis" },
          { key: "architecture", label: "Architecture", count: s.component_count },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="mt-4">
        {tab === "analysis" ? (
          !report ? (
            <Panel>
              <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
                <p className="max-w-md text-sm text-muted">
                  Run an analysis to evaluate this system against the DPDP / RBI /
                  CERT-In / MeitY controls its architecture puts in scope. The engine
                  is deterministic — every status is driven by declared facts and
                  observed architecture, never a model guess.
                </p>
                <Button
                  variant="primary"
                  onClick={() => analyze.mutate(id)}
                  disabled={analyze.isPending}
                >
                  <PlayCircle className="h-4 w-4" />
                  {analyze.isPending ? "Analyzing…" : "Analyze now"}
                </Button>
              </div>
            </Panel>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <Panel
                  title="Control posture"
                  actions={
                    <span className="text-xs text-muted">
                      {report.summary.applicable} applicable ·{" "}
                      {report.summary.total} evaluated
                    </span>
                  }
                >
                  <Table>
                    <THead>
                      <tr>
                        <TH>Control</TH>
                        <TH>Scope</TH>
                        <TH>Status</TH>
                        <TH>Reason</TH>
                      </tr>
                    </THead>
                    <TBodyRows
                      rows={sortedControls}
                      render={(c) => (
                        <tr
                          key={c.code}
                          className="border-b border-border/60 align-top"
                        >
                          <td className="px-4 py-2.5">
                            <div className="font-mono text-xs">{c.code}</div>
                            <div className="text-sm">{c.title}</div>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="text-xs text-muted">
                              {c.scope === "system" ? "System" : "Org-wide"}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            <Badge label={c.status} />
                          </td>
                          <td className="px-4 py-2.5 text-xs text-muted">
                            {c.reason}
                            {c.recommended_actions &&
                              c.recommended_actions.length > 0 && (
                                <ul className="mt-1 list-disc pl-4">
                                  {c.recommended_actions.map((a, i) => (
                                    <li key={i}>{a}</li>
                                  ))}
                                </ul>
                              )}
                          </td>
                        </tr>
                      )}
                    />
                  </Table>
                </Panel>
              </div>

              <div className="space-y-4">
                <Panel title="Derived facts">
                  <div className="space-y-2 p-4">
                    {FACT_KEYS.map(({ key, label }) => {
                      const p = report.fact_provenance[key];
                      return (
                        <div
                          key={key}
                          className="flex items-center justify-between gap-2 border-b border-border/40 pb-1.5 last:border-0"
                        >
                          <div className="text-xs text-muted">{label}</div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm">
                              {factValue(report.facts[key])}
                            </span>
                            {p && <ProvenanceBadge p={p} />}
                          </div>
                        </div>
                      );
                    })}
                    <p className="pt-2 text-[10px] leading-relaxed text-muted">
                      Declared / Observed facts are high-confidence. Inferred facts
                      come from the absence of evidence and warrant confirmation.
                    </p>
                  </div>
                </Panel>

                <ChangeImpactPanel changes={report.changes} />
              </div>
            </div>
          )
        ) : (
          <div className="space-y-4">
            <Panel title="Components">
              {components.isLoading ? (
                <Spinner />
              ) : !components.data || components.data.length === 0 ? (
                <EmptyState message="No components recorded for this system." />
              ) : (
                <Table>
                  <THead>
                    <tr>
                      <TH>Name</TH>
                      <TH>Type</TH>
                      <TH>Region</TH>
                      <TH>External</TH>
                      <TH>Provider</TH>
                    </tr>
                  </THead>
                  <TBodyRows
                    rows={components.data}
                    render={(c) => (
                      <tr key={c.id} className="border-b border-border/60">
                        <td className="px-4 py-2.5 font-medium">{c.name}</td>
                        <td className="px-4 py-2.5 text-muted">
                          {titleCase(c.component_type)}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {c.region || "—"}
                        </td>
                        <td className="px-4 py-2.5">
                          {c.external ? (
                            <Badge label="EXTERNAL" variant="HIGH" />
                          ) : (
                            <span className="text-xs text-muted">Internal</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {c.provider || "—"}
                        </td>
                      </tr>
                    )}
                  />
                </Table>
              )}
            </Panel>

            <Panel title="Data flows">
              {flows.isLoading ? (
                <Spinner />
              ) : !flows.data || flows.data.length === 0 ? (
                <EmptyState message="No data flows recorded for this system." />
              ) : (
                <Table>
                  <THead>
                    <tr>
                      <TH>Relation</TH>
                      <TH>Purpose</TH>
                      <TH>Personal data</TH>
                      <TH>Cross-border</TH>
                    </tr>
                  </THead>
                  <TBodyRows
                    rows={flows.data}
                    render={(f) => (
                      <tr key={f.id} className="border-b border-border/60">
                        <td className="px-4 py-2.5 text-muted">
                          {titleCase(f.relation)}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {f.purpose || "—"}
                        </td>
                        <td className="px-4 py-2.5">
                          {f.contains_personal_data ? "Yes" : "No"}
                        </td>
                        <td className="px-4 py-2.5">
                          {f.cross_border ? (
                            <Badge label="CROSS_BORDER" variant="HIGH" />
                          ) : (
                            "No"
                          )}
                        </td>
                      </tr>
                    )}
                  />
                </Table>
              )}
            </Panel>
          </div>
        )}
      </div>
    </>
  );
}
