"use client";

import { Button } from "@/components/button";
import { EmptyState, Panel, Spinner } from "@/components/panel";
import { PageHeader } from "@/components/ui";
import { downloadUrl } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useExecutiveReport } from "@/lib/queries";
import { Download, FileText } from "lucide-react";

type ReportDef = {
  name: string;
  description: string;
  formats: { label: string; href: string }[];
};

const REPORTS: ReportDef[] = [
  {
    name: "Executive Report",
    description:
      "Board-level posture summary: inventory, findings, control posture, and risks.",
    formats: [
      { label: "JSON", href: downloadUrl("/reports/executive") },
      { label: "PDF", href: downloadUrl("/reports/executive/pdf") },
    ],
  },
  {
    name: "Findings Report",
    description: "All findings with severity, status, risk score, and mapping.",
    formats: [
      { label: "CSV", href: downloadUrl("/reports/findings?fmt=csv") },
      { label: "JSON", href: downloadUrl("/reports/findings?fmt=json") },
    ],
  },
  {
    name: "Data Inventory Report",
    description: "Discovered assets, classification, and personal-data mapping.",
    formats: [
      { label: "CSV", href: downloadUrl("/reports/data-inventory?fmt=csv") },
      { label: "JSON", href: downloadUrl("/reports/data-inventory?fmt=json") },
    ],
  },
  {
    name: "Audit Trail Report",
    description: "Chronological record of governance-relevant mutations.",
    formats: [
      { label: "CSV", href: downloadUrl("/reports/audit?fmt=csv") },
      { label: "JSON", href: downloadUrl("/reports/audit?fmt=json") },
    ],
  },
];

export default function ReportsPage() {
  const exec = useExecutiveReport();
  const disclaimer = (exec.data?.disclaimer as string) || null;
  const summary = exec.data?.summary as Record<string, unknown> | undefined;

  return (
    <>
      <PageHeader
        title="Reports"
        description="Generate governance and control-assessment reports for auditors and leadership."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {REPORTS.map((r) => (
          <Panel key={r.name}>
            <div className="p-4">
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 h-5 w-5 text-accent" />
                <div className="flex-1">
                  <div className="text-sm font-semibold">{r.name}</div>
                  <p className="mt-0.5 text-xs text-muted">{r.description}</p>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                {r.formats.map((f) => (
                  <a key={f.label} href={f.href} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="secondary">
                      <Download className="h-3 w-3" />
                      {f.label}
                    </Button>
                  </a>
                ))}
              </div>
            </div>
          </Panel>
        ))}
      </div>

      <Panel title="Executive Report Preview" className="mt-4">
        {exec.isLoading ? (
          <Spinner />
        ) : !exec.data ? (
          <EmptyState message="Executive report is unavailable." />
        ) : (
          <div className="p-4">
            {summary && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
                {Object.entries(summary)
                  .filter(
                    ([, v]) =>
                      typeof v === "number" || typeof v === "string",
                  )
                  .filter(([k]) => k !== "assessment_date" && k !== "organization")
                  .map(([k, v]) => (
                    <div
                      key={k}
                      className="rounded border border-border bg-panel-2 px-3 py-2"
                    >
                      <div className="text-[10px] uppercase tracking-wide text-muted">
                        {titleCase(k)}
                      </div>
                      <div className="mt-0.5 text-sm font-semibold tabular-nums">
                        {String(v)}
                      </div>
                    </div>
                  ))}
              </div>
            )}
            {disclaimer && (
              <p className="mt-4 border-t border-border pt-3 text-xs italic text-muted">
                {disclaimer}
              </p>
            )}
          </div>
        )}
      </Panel>
    </>
  );
}
