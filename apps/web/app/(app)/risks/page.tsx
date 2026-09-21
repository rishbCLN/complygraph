"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, Field, Input, PageHeader, Select } from "@/components/ui";
import { cn, formatNumber } from "@/lib/format";
import { useCreateRisk, useRiskSummary, useRisks } from "@/lib/queries";
import type { Risk } from "@/lib/types";
import Link from "next/link";
import { useState } from "react";

const CATEGORIES = [
  "PRIVACY",
  "SECURITY",
  "OPERATIONAL",
  "COMPLIANCE",
  "VENDOR",
  "AI",
  "FINANCIAL",
  "REPUTATIONAL",
];

const STATUSES = ["IDENTIFIED", "ASSESSED", "TREATING", "ACCEPTED", "MITIGATED", "CLOSED"];

// Heatmap cell tone from a 1..25 likelihood*impact score.
function cellTone(score: number): string {
  if (score >= 20) return "bg-critical/70 text-white";
  if (score >= 12) return "bg-high/70 text-white";
  if (score >= 6) return "bg-medium/60 text-fg";
  return "bg-low/50 text-fg";
}

function Heatmap({ grid }: { grid: number[][] }) {
  // grid[impact-1][likelihood-1]; render impact 5 at top, likelihood 1..5 left→right.
  return (
    <div className="p-4">
      <div className="flex">
        <div className="flex flex-col justify-between pr-2 text-[10px] text-muted">
          <span className="rotate-180 [writing-mode:vertical-rl] self-center py-2">
            Impact →
          </span>
        </div>
        <div className="flex-1">
          <div className="grid grid-cols-5 gap-1">
            {[5, 4, 3, 2, 1].map((impact) =>
              [1, 2, 3, 4, 5].map((likelihood) => {
                const count = grid[impact - 1]?.[likelihood - 1] ?? 0;
                const score = impact * likelihood;
                return (
                  <div
                    key={`${impact}-${likelihood}`}
                    className={cn(
                      "flex aspect-square items-center justify-center rounded text-sm font-semibold tabular-nums",
                      count > 0 ? cellTone(score) : "bg-panel-2 text-muted/40",
                    )}
                    title={`Likelihood ${likelihood} × Impact ${impact} = ${score}`}
                  >
                    {count > 0 ? count : ""}
                  </div>
                );
              }),
            )}
          </div>
          <div className="mt-1 text-center text-[10px] text-muted">Likelihood →</div>
        </div>
      </div>
    </div>
  );
}

export default function RisksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const risks = useRisks({
    status: statusFilter || undefined,
    category: categoryFilter || undefined,
  });
  const summary = useRiskSummary();
  const create = useCreateRisk();

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    category: "COMPLIANCE",
    owner: "",
    inherent_likelihood: 3,
    inherent_impact: 3,
    residual_likelihood: 3,
    residual_impact: 3,
    single_loss_expectancy: "",
    annual_rate_of_occurrence: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit() {
    setError(null);
    if (!form.title.trim()) {
      setError("A risk needs a title.");
      return;
    }
    try {
      await create.mutateAsync({
        title: form.title.trim(),
        category: form.category,
        owner: form.owner || undefined,
        description: form.description || undefined,
        inherent_likelihood: form.inherent_likelihood,
        inherent_impact: form.inherent_impact,
        residual_likelihood: form.residual_likelihood,
        residual_impact: form.residual_impact,
        single_loss_expectancy: form.single_loss_expectancy
          ? Number(form.single_loss_expectancy)
          : undefined,
        annual_rate_of_occurrence: form.annual_rate_of_occurrence
          ? Number(form.annual_rate_of_occurrence)
          : undefined,
      });
      setOpen(false);
      setForm((f) => ({ ...f, title: "", owner: "", description: "" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the risk.");
    }
  }

  return (
    <>
      <PageHeader
        title="Risk register"
        description="Track risks with inherent and residual scoring, quantify exposure (annualised loss expectancy) and document acceptance decisions."
        actions={
          <Button variant="primary" onClick={() => setOpen(true)}>
            New risk
          </Button>
        }
      />

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="grid grid-cols-2 gap-4 lg:col-span-2 lg:grid-cols-2">
          <MetricCard label="Total risks" value={summary.data?.total ?? "—"} />
          <MetricCard
            label="Open"
            value={summary.data?.open ?? "—"}
            tone={summary.data && summary.data.open > 0 ? "warn" : "good"}
          />
          <MetricCard
            label="Critical (residual)"
            value={summary.data?.by_severity?.CRITICAL ?? "—"}
            tone={summary.data && summary.data.by_severity?.CRITICAL > 0 ? "critical" : "default"}
          />
          <MetricCard
            label="Annualised loss exposure"
            value={summary.data ? `$${formatNumber(summary.data.total_ale)}` : "—"}
            hint="Sum of SLE × ARO across risks"
          />
        </div>
        <Panel title="Residual risk heatmap">
          {summary.isLoading ? (
            <Spinner />
          ) : summary.data ? (
            <Heatmap grid={summary.data.heatmap} />
          ) : (
            <EmptyState message="No data." />
          )}
        </Panel>
      </div>

      <Panel
        title="Risks"
        actions={
          <div className="flex items-center gap-2">
            <Select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </div>
        }
      >
        {risks.isLoading ? (
          <Spinner />
        ) : risks.isError ? (
          <ErrorState message="Could not load risks." />
        ) : !risks.data || risks.data.length === 0 ? (
          <EmptyState message="No risks recorded yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Title</TH>
                <TH>Category</TH>
                <TH>Status</TH>
                <TH>Inherent</TH>
                <TH>Residual</TH>
                <TH>ALE</TH>
                <TH>Owner</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={risks.data}
              render={(r: Risk) => (
                <tr key={r.id} className="border-b border-border/60 align-top">
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/risks/${r.id}`}
                      className="text-sm font-medium text-accent hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted">{r.category}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={r.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-1.5">
                      <Badge label={r.inherent_severity} />
                      <span className="text-xs tabular-nums text-muted">{r.inherent_score}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-1.5">
                      <Badge label={r.residual_severity} />
                      <span className="text-xs tabular-nums text-muted">{r.residual_score}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs tabular-nums text-muted">
                    {r.ale != null ? `$${formatNumber(r.ale)}` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted">{r.owner || "—"}</td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <Drawer open={open} onClose={() => setOpen(false)} title="New risk">
        <div className="space-y-4">
          <Field
            label="Title"
            value={
              <Input
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder="e.g. Unencrypted database backups"
                className="w-full"
              />
            }
          />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Category"
              value={
                <Select
                  value={form.category}
                  onChange={(e) => set("category", e.target.value)}
                  className="w-full"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              }
            />
            <Field
              label="Owner (optional)"
              value={
                <Input
                  value={form.owner}
                  onChange={(e) => set("owner", e.target.value)}
                  placeholder="name@org"
                  className="w-full"
                />
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Inherent likelihood (1–5)"
              value={
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={form.inherent_likelihood}
                  onChange={(e) => set("inherent_likelihood", Number(e.target.value))}
                  className="w-full"
                />
              }
            />
            <Field
              label="Inherent impact (1–5)"
              value={
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={form.inherent_impact}
                  onChange={(e) => set("inherent_impact", Number(e.target.value))}
                  className="w-full"
                />
              }
            />
            <Field
              label="Residual likelihood (1–5)"
              value={
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={form.residual_likelihood}
                  onChange={(e) => set("residual_likelihood", Number(e.target.value))}
                  className="w-full"
                />
              }
            />
            <Field
              label="Residual impact (1–5)"
              value={
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={form.residual_impact}
                  onChange={(e) => set("residual_impact", Number(e.target.value))}
                  className="w-full"
                />
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Single loss expectancy ($)"
              value={
                <Input
                  type="number"
                  value={form.single_loss_expectancy}
                  onChange={(e) => set("single_loss_expectancy", e.target.value)}
                  placeholder="optional"
                  className="w-full"
                />
              }
            />
            <Field
              label="Annual rate of occurrence"
              value={
                <Input
                  type="number"
                  step="0.1"
                  value={form.annual_rate_of_occurrence}
                  onChange={(e) => set("annual_rate_of_occurrence", e.target.value)}
                  placeholder="e.g. 0.5"
                  className="w-full"
                />
              }
            />
          </div>

          <Field
            label="Description (optional)"
            value={
              <textarea
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
                rows={3}
                className="w-full rounded border border-border bg-panel-2 px-2.5 py-1.5 text-sm outline-none focus:border-accent"
              />
            }
          />

          <p className="text-xs text-muted">
            Score = likelihood × impact (1–25). Inherent is before controls, residual is after.
            Annualised loss expectancy = SLE × ARO when both are provided.
          </p>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submit} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create risk"}
            </Button>
          </div>
        </div>
      </Drawer>
    </>
  );
}
