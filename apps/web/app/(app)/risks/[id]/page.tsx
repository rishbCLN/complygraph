"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { ErrorState, Panel } from "@/components/panel";
import { ConfirmDialog, Field, Input, PageHeader, ScoreBar, Skeleton } from "@/components/ui";
import { formatDate, formatDateTime, formatNumber } from "@/lib/format";
import {
  useAcceptRisk,
  useCloseRisk,
  useDeleteRisk,
  useRisk,
  useSubmitApproval,
} from "@/lib/queries";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

export default function RiskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const risk = useRisk(id);
  const accept = useAcceptRisk();
  const close = useCloseRisk();
  const remove = useDeleteRisk();
  const submitApproval = useSubmitApproval();

  const [rationale, setRationale] = useState("");
  const [expires, setExpires] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (risk.isLoading) {
    return (
      <>
        <PageHeader title="Risk" breadcrumbs={[{ label: "Risk register", href: "/risks" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (risk.isError || !risk.data) {
    return (
      <>
        <PageHeader title="Risk" breadcrumbs={[{ label: "Risk register", href: "/risks" }]} />
        <ErrorState message="This risk could not be loaded." />
      </>
    );
  }

  const r = risk.data;
  const isAccepted = r.status === "ACCEPTED";
  const isClosed = r.status === "CLOSED";

  async function doAccept() {
    setError(null);
    if (!rationale.trim()) {
      setError("An acceptance decision requires a rationale.");
      return;
    }
    try {
      await accept.mutateAsync({
        id: r.id,
        rationale: rationale.trim(),
        expires_at: expires ? new Date(expires).toISOString() : undefined,
      });
      setRationale("");
      setExpires("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not accept the risk.");
    }
  }

  async function requestApproval() {
    setError(null);
    setNotice(null);
    if (!rationale.trim()) {
      setError("An acceptance decision requires a rationale.");
      return;
    }
    try {
      await submitApproval.mutateAsync({
        entity_type: "risk",
        entity_id: r.id,
        action: "accept",
        payload: {
          rationale: rationale.trim(),
          expires_at: expires ? new Date(expires).toISOString() : undefined,
        },
        summary: `Accept risk: ${r.title}`,
      });
      setRationale("");
      setExpires("");
      setNotice("Submitted for approval. A reviewer must approve it before it takes effect.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit for approval.");
    }
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: "Risk register", href: "/risks" }, { label: r.title }]}
        title={
          <span className="flex items-center gap-3">
            {r.title}
            <Badge label={r.status} />
          </span>
        }
        description={r.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            {!isClosed && (
              <Button variant="secondary" onClick={() => close.mutate(r.id)} disabled={close.isPending}>
                Close
              </Button>
            )}
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Scoring" className="lg:col-span-2">
          <div className="space-y-4 p-4">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Inherent (before controls)
                </span>
                <span className="flex items-center gap-2">
                  <Badge label={r.inherent_severity} />
                  <span className="text-sm tabular-nums">{r.inherent_score}/25</span>
                </span>
              </div>
              <ScoreBar label="Likelihood" value={r.inherent_likelihood} />
              <ScoreBar label="Impact" value={r.inherent_impact} />
            </div>
            <div className="border-t border-border/60 pt-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Residual (after controls)
                </span>
                <span className="flex items-center gap-2">
                  <Badge label={r.residual_severity} />
                  <span className="text-sm tabular-nums">{r.residual_score}/25</span>
                </span>
              </div>
              <ScoreBar label="Likelihood" value={r.residual_likelihood} />
              <ScoreBar label="Impact" value={r.residual_impact} />
            </div>
          </div>
        </Panel>

        <Panel title="Quantification">
          <div className="grid grid-cols-1 gap-3 p-4">
            <Field
              label="Single loss expectancy"
              value={r.single_loss_expectancy != null ? `$${formatNumber(r.single_loss_expectancy)}` : "—"}
            />
            <Field
              label="Annual rate of occurrence"
              value={r.annual_rate_of_occurrence != null ? r.annual_rate_of_occurrence : "—"}
            />
            <Field
              label="Annualised loss expectancy"
              value={r.ale != null ? `$${formatNumber(r.ale)}` : "—"}
            />
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Treatment" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 p-4">
            <Field label="Strategy" value={<Badge label={r.treatment_strategy} />} />
            <Field label="Category" value={r.category} />
            <Field label="Owner" value={r.owner || "—"} />
            <Field label="Created" value={formatDate(r.created_at)} />
            <div className="col-span-2">
              <Field label="Treatment plan" value={r.treatment_plan || "—"} />
            </div>
          </div>
        </Panel>

        <Panel title="Business impact analysis">
          <div className="grid grid-cols-1 gap-3 p-4">
            <Field
              label="Recovery time objective (RTO)"
              value={r.rto_hours != null ? `${r.rto_hours} h` : "—"}
            />
            <Field
              label="Recovery point objective (RPO)"
              value={r.rpo_hours != null ? `${r.rpo_hours} h` : "—"}
            />
            <Field
              label="Max tolerable downtime"
              value={r.max_tolerable_downtime_hours != null ? `${r.max_tolerable_downtime_hours} h` : "—"}
            />
            <Field label="Business impact" value={r.business_impact || "—"} />
          </div>
        </Panel>
      </div>

      <Panel title="Risk acceptance" className="mt-4">
        {isAccepted ? (
          <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
            <Field label="Accepted at" value={formatDateTime(r.accepted_at)} />
            <Field label="Review due" value={r.acceptance_expires_at ? formatDate(r.acceptance_expires_at) : "No expiry set"} />
            <div className="sm:col-span-2">
              <Field label="Rationale" value={r.acceptance_rationale || "—"} />
            </div>
          </div>
        ) : isClosed ? (
          <div className="p-4 text-sm text-muted">This risk is closed.</div>
        ) : (
          <div className="space-y-3 p-4">
            <p className="text-sm text-muted">
              Formally accept the residual risk. Acceptance is recorded against your account with a
              rationale and an optional review date, so it cannot silently persist.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Rationale"
                value={
                  <Input
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    placeholder="Why is this residual risk acceptable?"
                    className="w-full"
                  />
                }
              />
              <Field
                label="Review by (optional)"
                value={
                  <Input
                    type="date"
                    value={expires}
                    onChange={(e) => setExpires(e.target.value)}
                    className="w-full"
                  />
                }
              />
            </div>
            {error && <div className="text-sm text-danger">{error}</div>}
            {notice && <div className="text-sm text-pass">{notice}</div>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={requestApproval}
                disabled={submitApproval.isPending}
                title="Submit this acceptance for maker-checker review"
              >
                {submitApproval.isPending ? "Submitting…" : "Request approval"}
              </Button>
              <Button variant="primary" onClick={doAccept} disabled={accept.isPending}>
                {accept.isPending ? "Recording…" : "Accept risk"}
              </Button>
            </div>
          </div>
        )}
      </Panel>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete risk"
        message="This permanently removes the risk from the register. This cannot be undone."
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await remove.mutateAsync(r.id);
          router.push("/risks");
        }}
      />
    </>
  );
}
