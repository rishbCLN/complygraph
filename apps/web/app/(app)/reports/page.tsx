"use client";

import { Button } from "@/components/button";
import { EmptyState, Panel, Spinner } from "@/components/panel";
import { PageHeader } from "@/components/ui";
import { downloadUrl } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useAiSystems, useExecutiveReport } from "@/lib/queries";
import { BrainCircuit, Download, FileText } from "lucide-react";

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
  const systems = useAiSystems();
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

      <Panel
        title={
          <span className="flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-accent" />
            Per-System Compliance Reports
          </span>
        }
        className="mt-4"
      >
        {systems.isLoading ? (
          <Spinner />
        ) : !systems.data || systems.data.length === 0 ? (
          <EmptyState message="No AI systems to report on yet." />
        ) : (
          <div className="divide-y divide-border">
            {systems.data.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <div>
                  <div className="text-sm font-medium">{s.name}</div>
                  <p className="mt-0.5 text-xs uppercase text-muted">
                    {s.sector} · {s.system_type} · {s.lifecycle_stage}
                  </p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={downloadUrl(`/reports/system/${s.id}`)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Button size="sm" variant="secondary">
                      <Download className="h-3 w-3" />
                      JSON
                    </Button>
                  </a>
                  <a
                    href={downloadUrl(`/reports/system/${s.id}/pdf`)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Button size="sm" variant="secondary">
                      <Download className="h-3 w-3" />
                      PDF
                    </Button>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

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
