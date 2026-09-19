"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Input, PageHeader, Select } from "@/components/ui";
import { formatDate, formatNumber, titleCase } from "@/lib/format";
import { useAssets } from "@/lib/queries";
import { useRouter } from "next/navigation";
import { useState } from "react";

const CLASSIFICATIONS = [
  "PERSONAL_DATA",
  "SENSITIVE_PERSONAL_DATA",
  "NON_PERSONAL",
  "UNKNOWN",
];

export default function DataAssetsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [classification, setClassification] = useState("");
  const { data, isLoading, isError } = useAssets({
    search: search || undefined,
    classification: classification || undefined,
  });

  return (
    <>
      <PageHeader
        title="Data Assets"
        description="Discovered databases, datasets, files, and applications holding data."
        actions={
          <div className="flex items-center gap-2">
            <Input
              placeholder="Search assets…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-48"
            />
            <Select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
            >
              <option value="">All classifications</option>
              {CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {titleCase(c)}
                </option>
              ))}
            </Select>
          </div>
        }
      />
      <Panel title={data ? `${data.total} assets` : "Assets"}>
        {isLoading ? (
          <Spinner />
        ) : isError ? (
          <ErrorState message="Could not load data assets." />
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No assets match these filters." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Type</TH>
                <TH>Classification</TH>
                <TH>Sensitivity</TH>
                <TH>Personal</TH>
                <TH>Fields</TH>
                <TH>Owner</TH>
                <TH>Last Seen</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={data.items}
              render={(a) => (
                <tr
                  key={a.id}
                  onClick={() => router.push(`/data-assets/${a.id}`)}
                  className="cursor-pointer border-b border-border/60 hover:bg-panel-2"
                >
                  <td className="px-4 py-2.5 font-medium">
                    {a.display_name || a.name}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {titleCase(a.asset_type)}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge
                      label={titleCase(a.classification)}
                      variant={
                        a.classification === "SENSITIVE_PERSONAL_DATA"
                          ? "HIGH"
                          : a.classification === "PERSONAL_DATA"
                            ? "MEDIUM"
                            : "NOT_APPLICABLE"
                      }
                    />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {a.sensitivity_level}/5
                  </td>
                  <td className="px-4 py-2.5">
                    {a.personal_data ? (
                      <span className="text-medium">Yes</span>
                    ) : (
                      <span className="text-muted">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {a.field_count}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{a.owner || "—"}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDate(a.last_seen_at)}
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
