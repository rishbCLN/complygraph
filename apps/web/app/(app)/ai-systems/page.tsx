"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useAiSystems, useAnalyzeAllSystemsMutation } from "@/lib/queries";
import type { PortfolioRollup } from "@/lib/types";
import { PlayCircle } from "lucide-react";
import { useRouter } from "next/navigation";

function riskTone(high: boolean): "critical" | "default" {
  return high ? "critical" : "default";
}

export default function AiSystemsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useAiSystems();
  const analyzeAll = useAnalyzeAllSystemsMutation();
  const rollup: PortfolioRollup | undefined = analyzeAll.data;

  const production = data?.filter((s) => s.lifecycle_stage === "PRODUCTION").length ?? 0;
  const highRisk = data?.filter((s) => s.high_risk).length ?? 0;

  return (
    <>
      <PageHeader
        title="AI Systems"
        description="AI-system-centric compliance across DPDP, RBI, CERT-In and MeitY. Each system is analyzed against the controls its architecture puts in scope."
        actions={
          <Button
            variant="primary"
            onClick={() => analyzeAll.mutate()}
            disabled={analyzeAll.isPending || !data || data.length === 0}
          >
            <PlayCircle className="h-4 w-4" />
            {analyzeAll.isPending ? "Analyzing…" : "Analyze all"}
          </Button>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="Systems" value={data?.length ?? "—"} />
        <MetricCard label="In production" value={production} />
        <MetricCard
          label="High risk"
          value={highRisk}
          tone={riskTone(highRisk > 0)}
        />
        {rollup ? (
          <MetricCard
            label="Systems with gaps"
            value={rollup.systems_with_failures}
            hint={`${rollup.total_regressions} regression${rollup.total_regressions === 1 ? "" : "s"} since last run`}
            tone={rollup.systems_with_failures > 0 ? "warn" : "good"}
          />
        ) : (
          <MetricCard label="Systems with gaps" value="—" hint="Run Analyze all" />
        )}
      </div>

      {rollup && (
        <Panel title="Latest portfolio analysis" className="mb-4">
          <div className="p-4 text-sm text-muted">
            Analyzed {rollup.system_count} system
            {rollup.system_count === 1 ? "" : "s"} as of{" "}
            {rollup.assessment_date}. {rollup.systems_with_failures} have failing or
            unevidenced controls; {rollup.total_regressions} control
            {rollup.total_regressions === 1 ? "" : "s"} regressed since the previous
            snapshot.
          </div>
        </Panel>
      )}

      <Panel title={data ? `${data.length} systems` : "AI Systems"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load AI systems." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No AI systems inventoried yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>System</TH>
                <TH>Sector</TH>
                <TH>Type</TH>
                <TH>Stage</TH>
                <TH>Review</TH>
                <TH>Risk</TH>
                <TH>Components</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(s) => (
                <tr
                  key={s.id}
                  onClick={() => router.push(`/ai-systems/${s.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5">
                    <div className="font-medium">{s.name}</div>
                    {s.owner && (
                      <div className="text-xs text-muted">Owner: {s.owner}</div>
                    )}
                  </td>
                  <td className="px-4 py-2.5 uppercase text-muted">{s.sector}</td>
                  <td className="px-4 py-2.5 text-muted">{s.system_type}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={s.lifecycle_stage} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={s.review_status} />
                  </td>
                  <td className="px-4 py-2.5">
                    {s.high_risk ? (
                      <Badge label="HIGH_RISK" />
                    ) : (
                      <span className="text-xs text-muted">Standard</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {s.component_count} / {s.flow_count} flows
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
