"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader, Tabs } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useApprovals, useMe, useReviewApproval } from "@/lib/queries";
import type { ApprovalRequest } from "@/lib/types";
import { useState } from "react";

const TABS = [
  { key: "PENDING", label: "Pending" },
  { key: "APPROVED", label: "Approved" },
  { key: "REJECTED", label: "Rejected" },
  { key: "", label: "All" },
];

function actionLabel(r: ApprovalRequest): string {
  const map: Record<string, string> = {
    resolve: "Resolve finding",
    accept_risk: "Accept risk (finding)",
    false_positive: "Mark false positive",
    accept: "Accept risk",
    sign_off: "Sign off assessment",
  };
  return map[r.action] || r.action;
}

export default function ApprovalsPage() {
  const [tab, setTab] = useState("PENDING");
  const me = useMe();
  const approvals = useApprovals({ status: tab || undefined });
  const review = useReviewApproval();
  const [error, setError] = useState<string | null>(null);

  const canApprove = me.data?.capabilities?.includes("approve_requests") ?? false;
  const myId = me.data?.id;

  async function act(id: string, decision: "approve" | "reject" | "cancel") {
    setError(null);
    try {
      await review.mutateAsync({ id, decision });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not complete the review.");
    }
  }

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Maker-checker queue. Sensitive changes (finding resolutions, risk acceptances, assessment sign-offs) are proposed by one person and approved by another. A submitter cannot approve their own request."
      />

      <div className="mb-4">
        <Tabs tabs={TABS} active={tab} onChange={setTab} />
      </div>

      {error && <div className="mb-3 text-sm text-danger">{error}</div>}

      <Panel title="Requests">
        {approvals.isLoading ? (
          <Spinner />
        ) : approvals.isError ? (
          <ErrorState message="Could not load approvals." />
        ) : !approvals.data || approvals.data.length === 0 ? (
          <EmptyState message="Nothing here." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Change</TH>
                <TH>Target</TH>
                <TH>Status</TH>
                <TH>Submitted</TH>
                <TH>Note</TH>
                <TH> </TH>
              </tr>
            </THead>
            <TBodyRows
              rows={approvals.data}
              render={(r: ApprovalRequest) => {
                const isPending = r.status === "PENDING";
                const isMine = myId && r.submitted_by === myId;
                const payloadNote =
                  (r.payload?.note as string) ||
                  (r.payload?.rationale as string) ||
                  r.review_note ||
                  "—";
                return (
                  <tr key={r.id} className="border-b border-border/60 align-top">
                    <td className="px-4 py-2.5">
                      <div className="text-sm font-medium">{actionLabel(r)}</div>
                      {r.summary && <div className="text-xs text-muted">{r.summary}</div>}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted">{r.entity_type}</td>
                    <td className="px-4 py-2.5">
                      <Badge label={r.status} />
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted">
                      {formatDateTime(r.submitted_at)}
                    </td>
                    <td className="max-w-xs px-4 py-2.5 text-xs text-muted">{payloadNote}</td>
                    <td className="px-4 py-2.5">
                      {isPending && (
                        <div className="flex items-center gap-2">
                          {canApprove && !isMine && (
                            <>
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={() => act(r.id, "approve")}
                                disabled={review.isPending}
                              >
                                Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => act(r.id, "reject")}
                                disabled={review.isPending}
                              >
                                Reject
                              </Button>
                            </>
                          )}
                          {canApprove && !isMine ? null : isMine ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => act(r.id, "cancel")}
                              disabled={review.isPending}
                            >
                              Cancel
                            </Button>
                          ) : (
                            <span className="text-xs text-muted">Awaiting a reviewer</span>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              }}
            />
          </Table>
        )}
      </Panel>
    </>
  );
}
