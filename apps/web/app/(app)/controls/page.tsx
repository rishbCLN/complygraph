"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Input, PageHeader } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import { useControls } from "@/lib/queries";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ControlsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useControls({
    search: search || undefined,
  });

  return (
    <>
      <PageHeader
        title="Controls"
        description="DPDP-aligned control library with continuous assessment status."
        actions={
          <Input
            placeholder="Search controls…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
        }
      />
      <Panel title={data ? `${data.length} controls` : "Controls"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load controls." />
        ) : !data || data.length === 0 ? (
          <EmptyState message="No controls match your search." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Code</TH>
                <TH>Title</TH>
                <TH>Category</TH>
                <TH>Regulation</TH>
                <TH>Effective</TH>
                <TH>Status</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data}
              render={(c) => (
                <tr
                  key={c.id}
                  onClick={() => router.push(`/controls/${c.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5 font-mono text-xs">{c.code}</td>
                  <td className="px-4 py-2.5 font-medium">{c.title}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {titleCase(c.category)}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {c.regulation_name || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(c.effective_from)}
                  </td>
                  <td className="px-4 py-2.5">
                    {c.temporal_status === "upcoming" ? (
                      <Badge label="UPCOMING" />
                    ) : c.latest_status ? (
                      <Badge label={c.latest_status} />
                    ) : (
                      <Badge label="NO_EVIDENCE" />
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
