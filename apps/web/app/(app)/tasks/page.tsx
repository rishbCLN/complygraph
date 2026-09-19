"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { PageHeader } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import { useTaskMutation, useTasks } from "@/lib/queries";
import Link from "next/link";

export default function TasksPage() {
  const { data, isLoading, isError } = useTasks();
  const mutate = useTaskMutation();

  return (
    <>
      <PageHeader
        title="Tasks"
        description="Remediation work tracked against findings and controls."
      />
      <Panel title={data ? `${data.length} tasks` : "Tasks"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load tasks." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No remediation tasks." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Task</TH>
                <TH>Priority</TH>
                <TH>Status</TH>
                <TH>Finding</TH>
                <TH>Due</TH>
                <TH></TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(t) => (
                <tr key={t.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{t.title}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={t.priority} variant={t.priority} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={t.status} />
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {t.finding_id ? (
                      <Link
                        href={`/findings/${t.finding_id}`}
                        className="text-accent hover:underline"
                      >
                        View
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{formatDate(t.due_at)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {t.status !== "COMPLETED" && t.status !== "DONE" && (
                      <Button
                        size="sm"
                        onClick={() =>
                          mutate.mutate({ id: t.id, status: "COMPLETED" })
                        }
                        disabled={mutate.isPending}
                      >
                        Complete
                      </Button>
                    )}
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
