"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { ConfirmDialog, PageHeader, Skeleton } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import {
  useCampaign,
  useCampaignResults,
  useDeleteCampaign,
  useRunCampaign,
} from "@/lib/queries";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

function coverageTone(pct: number): "good" | "warn" | "critical" {
  if (pct >= 90) return "good";
  if (pct >= 70) return "warn";
  return "critical";
}

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const campaign = useCampaign(id);
  const results = useCampaignResults(id);
  const run = useRunCampaign();
  const remove = useDeleteCampaign();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (campaign.isLoading) {
    return (
      <>
        <PageHeader title="Campaign" breadcrumbs={[{ label: "Audit campaigns", href: "/campaigns" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (campaign.isError || !campaign.data) {
    return (
      <>
        <PageHeader title="Campaign" breadcrumbs={[{ label: "Audit campaigns", href: "/campaigns" }]} />
        <ErrorState message="This campaign could not be loaded." />
      </>
    );
  }

  const c = campaign.data;
  const isDraft = c.status === "DRAFT";
  const summary = c.summary;

  async function doRun() {
    setError(null);
    try {
      await run.mutateAsync(c.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not run the campaign.");
    }
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "Audit campaigns", href: "/campaigns" }, { label: c.name }]}
        title={
          <span className="flex items-center gap-3">
            {c.name}
            <Badge label={c.status} />
          </span>
        }
        description={c.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            {isDraft && (
              <Button variant="primary" onClick={doRun} disabled={run.isPending}>
                {run.isPending ? "Running…" : "Run campaign"}
              </Button>
            )}
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      {error && <div className="mb-3 text-sm text-danger">{error}</div>}

      {summary ? (
        <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            label="Coverage"
            value={`${summary.coverage}%`}
            hint="Passing / applicable"
            tone={coverageTone(summary.coverage)}
          />
          <MetricCard label="Controls assessed" value={summary.total} />
          <MetricCard label="Applicable" value={summary.applicable} />
          <MetricCard label="Passing" value={summary.passing} tone="good" />
        </div>
      ) : (
        <Panel className="mb-4">
          <EmptyState
            message={
              isDraft
                ? "This campaign has not run yet. Run it to freeze a point-in-time assessment."
                : "No summary available."
            }
          />
        </Panel>
      )}

      {c.assessment_date && (
        <p className="mb-4 text-xs text-muted">
          Assessed as of {formatDateTime(c.assessment_date)}
          {c.completed_at ? ` · completed ${formatDateTime(c.completed_at)}` : ""}
        </p>
      )}

      <Panel title="Results">
        {results.isLoading ? (
          <Spinner />
        ) : !results.data || results.data.length === 0 ? (
          <EmptyState message="No results. Run the campaign to populate them." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Control</TH>
                <TH>Framework</TH>
                <TH>Category</TH>
                <TH>Status</TH>
                <TH>Reason</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={results.data}
              render={(r) => (
                <tr key={r.id} className="border-b border-border/60 align-top">
                  <td className="px-4 py-2.5">
                    <span className="font-mono text-xs text-muted">{r.control_code}</span>
                    <div className="text-sm">{r.control_title}</div>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted">{r.regulation_name || "—"}</td>
                  <td className="px-4 py-2.5 text-xs text-muted">{r.category || "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={r.status} />
                  </td>
                  <td className="max-w-md px-4 py-2.5 text-xs text-muted">{r.reason || "—"}</td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete campaign"
        message="This permanently removes the campaign and its frozen results. This cannot be undone."
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await remove.mutateAsync(c.id);
          router.push("/campaigns");
        }}
      />
    </>
  );
}
