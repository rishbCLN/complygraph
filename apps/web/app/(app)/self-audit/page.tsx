"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { PageHeader } from "@/components/ui";
import { cn } from "@/lib/format";
import { useSelfAudit } from "@/lib/queries";
import { useState } from "react";

function scoreTone(score: number): string {
  if (score >= 90) return "text-pass";
  if (score >= 70) return "text-upcoming";
  return "text-danger";
}

function CheckRow({ check }: { check: import("@/lib/types").QualityCheck }) {
  const [open, setOpen] = useState(false);
  const hasGaps = check.incomplete > 0;
  return (
    <div className="border-b border-border/60">
      <button
        onClick={() => hasGaps && setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center gap-3 px-4 py-3 text-left",
          hasGaps ? "cursor-pointer hover:bg-panel-2" : "cursor-default",
        )}
      >
        <span className={cn("w-10 text-sm font-semibold tabular-nums", scoreTone(check.score))}>
          {check.score}
        </span>
        <span className="flex-1">
          <span className="text-sm font-medium">{check.title}</span>
          <span className="ml-2 text-xs text-muted">{check.category}</span>
        </span>
        <span className="text-xs text-muted">
          {check.complete}/{check.total} complete
        </span>
        {hasGaps ? (
          <Badge label={`${check.incomplete} GAP${check.incomplete === 1 ? "" : "S"}`} />
        ) : (
          <Badge label="OK" />
        )}
      </button>
      {open && hasGaps && (
        <div className="bg-panel-2 px-4 py-3">
          <p className="mb-2 text-xs text-muted">{check.recommendation}</p>
          <ul className="space-y-1">
            {check.items.map((item) => (
              <li key={item.id} className="flex items-center gap-2 text-xs">
                <span className="rounded bg-panel px-1.5 py-0.5 text-[10px] uppercase text-muted">
                  {item.type}
                </span>
                <span className="font-medium">{item.label}</span>
                <span className="text-muted">— {item.detail}</span>
              </li>
            ))}
            {check.items_truncated && (
              <li className="text-xs text-muted">…and more not shown.</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function SelfAuditPage() {
  const audit = useSelfAudit();

  return (
    <>
      <PageHeader
        title="Self-audit"
        description="Data-quality checks on your compliance inventory. Measures how complete and trustworthy the data is — not legal compliance."
      />
      {audit.isLoading ? (
        <Spinner />
      ) : audit.isError ? (
        <ErrorState message="Could not run the self-audit." />
      ) : !audit.data ? (
        <EmptyState message="No data-quality results." />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Panel title="Overall completeness">
              <div className="flex items-baseline gap-2 p-4">
                <span className={cn("text-4xl font-semibold tabular-nums", scoreTone(audit.data.overall_score))}>
                  {audit.data.overall_score}
                </span>
                <span className="text-sm text-muted">/ 100</span>
              </div>
            </Panel>
            <Panel title="Open data gaps">
              <div className="p-4 text-4xl font-semibold tabular-nums">
                {audit.data.total_gaps}
              </div>
            </Panel>
            <Panel title="Checks run">
              <div className="p-4 text-4xl font-semibold tabular-nums">
                {audit.data.check_count}
              </div>
            </Panel>
          </div>

          <Panel title="Quality checks">
            <div>
              {audit.data.checks.map((check) => (
                <CheckRow key={check.key} check={check} />
              ))}
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
