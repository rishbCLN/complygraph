"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows } from "@/components/table";
import { PageHeader, Skeleton } from "@/components/ui";
import { ErrorState } from "@/components/panel";
import { formatDate, formatDateTime, titleCase } from "@/lib/format";
import {
  useConnectors,
  useDashboardSummary,
  useDataPosture,
  useRiskTrend,
  useScanMutation,
  useScans,
  useTopFindings,
} from "@/lib/queries";
import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#3b82f6",
};

const STATUS_COLORS: Record<string, string> = {
  PASS: "#22c55e",
  PARTIAL: "#eab308",
  FAIL: "#ef4444",
  NO_EVIDENCE: "#f97316",
  UPCOMING: "#8b5cf6",
  NOT_APPLICABLE: "#8b95a7",
};

const FRESHNESS_COLORS: Record<string, string> = {
  FRESH: "#22c55e",
  STALE: "#eab308",
  EXPIRED: "#ef4444",
  UNKNOWN: "#8b95a7",
};

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded border border-border bg-panel px-2 py-1 text-xs shadow-lg">
      {label && <div className="mb-0.5 font-medium">{titleCase(String(label))}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} className="text-muted">
          {titleCase(p.name)}: <span className="text-fg">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const summary = useDashboardSummary();
  const riskTrend = useRiskTrend();
  const topFindings = useTopFindings(8);
  const posture = useDataPosture();
  const connectors = useConnectors();
  const scans = useScans();
  const scanMut = useScanMutation();

  const lastScan = scans.data?.[0]?.completed_at || scans.data?.[0]?.created_at;

  async function scanNow() {
    const list = connectors.data || [];
    if (list.length === 0) return;
    // Kick off a scan on every connector (eager when Redis is absent).
    await Promise.all(list.map((c) => scanMut.mutateAsync(c.id).catch(() => null)));
  }

  if (summary.isError) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <ErrorState message="Could not load dashboard metrics. Check the API is running." />
      </>
    );
  }

  const s = summary.data;

  const controlBreakdown = s
    ? Object.entries(s.control_status_breakdown).map(([status, count]) => ({
        status,
        count,
      }))
    : [];
  const freshness = s
    ? Object.entries(s.evidence_freshness).map(([status, count]) => ({
        status,
        count,
      }))
    : [];

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Internal Control Posture — continuous data governance overview"
        actions={
          <div className="flex items-center gap-3">
            <div className="text-right text-xs text-muted">
              <div>
                Assessment date:{" "}
                <span className="text-fg">{formatDate(s?.assessment_date)}</span>
              </div>
              <div>
                Last scan:{" "}
                <span className="text-fg">
                  {lastScan ? formatDateTime(lastScan) : "—"}
                </span>
              </div>
            </div>
            <Button
              variant="primary"
              onClick={scanNow}
              disabled={scanMut.isPending || (connectors.data || []).length === 0}
            >
              <RefreshCw
                className={
                  "h-3.5 w-3.5 " + (scanMut.isPending ? "animate-spin" : "")
                }
              />
              {scanMut.isPending ? "Scanning…" : "Scan Now"}
            </Button>
          </div>
        }
      />

      {summary.isLoading || !s ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          <MetricCard label="Data Assets" value={s.data_assets} />
          <MetricCard
            label="Personal Data Assets"
            value={s.personal_data_assets}
          />
          <MetricCard label="Open Findings" value={s.open_findings} tone="warn" />
          <MetricCard
            label="Critical Findings"
            value={s.critical_findings}
            tone={s.critical_findings > 0 ? "critical" : "good"}
          />
          <MetricCard
            label="Control Coverage"
            value={`${s.control_coverage}%`}
            tone={s.control_coverage >= 80 ? "good" : "warn"}
          />
          <MetricCard
            label="Evidence Stale"
            value={`${s.evidence_stale_pct}%`}
            tone={s.evidence_stale_pct > 20 ? "warn" : "good"}
          />
          <MetricCard
            label="Unmapped Data Flows"
            value={s.unmapped_data_flows}
            tone={s.unmapped_data_flows > 0 ? "warn" : "good"}
          />
          <MetricCard
            label="Vendors w/ Personal Data"
            value={s.vendors_processing_personal_data}
          />
          <MetricCard label="Upcoming Obligations" value={s.upcoming_obligations} />
        </div>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Risk Distribution">
          {riskTrend.isLoading ? (
            <Spinner />
          ) : !riskTrend.data || riskTrend.data.length === 0 ? (
            <EmptyState message="No findings to chart." />
          ) : (
            <div className="p-4">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={riskTrend.data}
                    dataKey="count"
                    nameKey="severity"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {riskTrend.data.map((d) => (
                      <Cell
                        key={d.severity}
                        fill={SEVERITY_COLORS[d.severity] || "#8b95a7"}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 flex flex-wrap justify-center gap-3">
                {riskTrend.data.map((d) => (
                  <div key={d.severity} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="h-2.5 w-2.5 rounded-sm"
                      style={{
                        background: SEVERITY_COLORS[d.severity] || "#8b95a7",
                      }}
                    />
                    <span className="text-muted">{titleCase(d.severity)}</span>
                    <span className="tabular-nums">{d.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Control Posture">
          {summary.isLoading ? (
            <Spinner />
          ) : controlBreakdown.length === 0 ? (
            <EmptyState message="No control assessments yet." />
          ) : (
            <div className="p-4">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={controlBreakdown} layout="vertical" margin={{ left: 20 }}>
                  <XAxis type="number" tick={{ fill: "#8b95a7", fontSize: 11 }} allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="status"
                    tick={{ fill: "#8b95a7", fontSize: 11 }}
                    tickFormatter={(v) => titleCase(v)}
                    width={90}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "#1f2937" }} />
                  <Bar dataKey="count" radius={[0, 3, 3, 0]}>
                    {controlBreakdown.map((d) => (
                      <Cell key={d.status} fill={STATUS_COLORS[d.status] || "#8b95a7"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Data Categories">
          {posture.isLoading ? (
            <Spinner />
          ) : !posture.data || posture.data.categories.length === 0 ? (
            <EmptyState message="No classified data categories." />
          ) : (
            <div className="p-4">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={posture.data.categories} margin={{ bottom: 10 }}>
                  <XAxis
                    dataKey="category"
                    tick={{ fill: "#8b95a7", fontSize: 10 }}
                    tickFormatter={(v) => titleCase(v)}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fill: "#8b95a7", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "#1f2937" }} />
                  <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Evidence Freshness">
          {summary.isLoading ? (
            <Spinner />
          ) : freshness.length === 0 ? (
            <EmptyState message="No evidence recorded." />
          ) : (
            <div className="p-4">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={freshness}>
                  <XAxis
                    dataKey="status"
                    tick={{ fill: "#8b95a7", fontSize: 11 }}
                    tickFormatter={(v) => titleCase(v)}
                  />
                  <YAxis tick={{ fill: "#8b95a7", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "#1f2937" }} />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {freshness.map((d) => (
                      <Cell key={d.status} fill={FRESHNESS_COLORS[d.status] || "#8b95a7"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Top Findings" className="mt-4">
        {topFindings.isLoading ? (
          <Spinner />
        ) : !topFindings.data || topFindings.data.length === 0 ? (
          <EmptyState message="No open findings. Nice work." />
        ) : (
          <Table>
            <thead className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Severity</th>
                <th className="px-4 py-2 font-medium">Finding</th>
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <TBodyRows
              rows={topFindings.data}
              render={(f) => (
                <tr
                  key={f.id}
                  onClick={() => router.push(`/findings/${f.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5">
                    <Badge label={f.severity} />
                  </td>
                  <td className="px-4 py-2.5">{f.title}</td>
                  <td className="px-4 py-2.5 tabular-nums">{f.risk_score}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={f.status} />
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>
    </>
  );
}
