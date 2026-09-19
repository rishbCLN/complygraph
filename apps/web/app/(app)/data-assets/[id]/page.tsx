"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { formatDateTime, formatNumber, titleCase } from "@/lib/format";
import {
  useAsset,
  useAssetControls,
  useAssetFields,
  useAssetFlows,
} from "@/lib/queries";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const asset = useAsset(id);
  const fields = useAssetFields(id);
  const flows = useAssetFlows(id);
  const controls = useAssetControls(id);
  const [tab, setTab] = useState("overview");

  if (asset.isLoading) {
    return (
      <>
        <PageHeader title="Asset" breadcrumbs={[{ label: "Data Assets", href: "/data-assets" }]} />
        <Skeleton className="h-64" />
      </>
    );
  }
  if (asset.isError || !asset.data) {
    return (
      <>
        <PageHeader title="Asset" breadcrumbs={[{ label: "Data Assets", href: "/data-assets" }]} />
        <ErrorState message="This asset could not be loaded." />
      </>
    );
  }

  const a = asset.data;

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: "Data Assets", href: "/data-assets" },
          { label: a.display_name || a.name },
        ]}
        title={a.display_name || a.name}
        description={titleCase(a.asset_type)}
        actions={
          <div className="flex items-center gap-2">
            {a.personal_data && <Badge label="Personal Data" variant="MEDIUM" />}
            <Badge label={`Sensitivity ${a.sensitivity_level}/5`} variant={a.sensitivity_level >= 4 ? "HIGH" : "LOW"} />
          </div>
        }
      />

      <div className="mb-4">
        <Tabs
          active={tab}
          onChange={setTab}
          tabs={[
            { key: "overview", label: "Overview" },
            { key: "fields", label: "Fields", count: fields.data?.length },
            { key: "flows", label: "Data Flows", count: flows.data?.length },
            { key: "controls", label: "Controls", count: controls.data?.length },
          ]}
        />
      </div>

      {tab === "overview" && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Panel>
            <div className="space-y-3 p-4">
              <Field label="Type" value={titleCase(a.asset_type)} />
              <Field label="System" value={a.system_name || "—"} />
              <Field label="Environment" value={titleCase(a.environment)} />
            </div>
          </Panel>
          <Panel>
            <div className="space-y-3 p-4">
              <Field label="Classification" value={titleCase(a.classification)} />
              <Field label="Sensitivity" value={`${a.sensitivity_level}/5`} />
              <Field label="Personal data" value={a.personal_data ? "Yes" : "No"} />
            </div>
          </Panel>
          <Panel>
            <div className="space-y-3 p-4">
              <Field label="Owner" value={a.owner || "—"} />
              <Field label="Row count" value={formatNumber(a.row_count)} />
              <Field label="Fields" value={a.field_count} />
            </div>
          </Panel>
          <Panel>
            <div className="space-y-3 p-4">
              <Field label="Last seen" value={formatDateTime(a.last_seen_at)} />
            </div>
          </Panel>
        </div>
      )}

      {tab === "fields" && (
        <Panel>
          {fields.isLoading ? (
            <Spinner />
          ) : !fields.data || fields.data.length === 0 ? (
            <EmptyState message="No fields discovered for this asset." />
          ) : (
            <Table>
              <THead>
                <tr>
                  <TH>Field</TH>
                  <TH>Data Type</TH>
                  <TH>Category</TH>
                  <TH>Classification</TH>
                  <TH>Confidence</TH>
                  <TH>Method</TH>
                  <TH>Review</TH>
                </tr>
              </THead>
              <TBodyRows
                rows={fields.data}
                render={(f) => (
                  <tr key={f.id} className="border-b border-border/60">
                    <td className="px-4 py-2.5 font-mono text-xs">{f.name}</td>
                    <td className="px-4 py-2.5 text-muted">
                      {f.data_type || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-muted">
                      {titleCase(f.category)}
                    </td>
                    <td className="px-4 py-2.5 text-muted">
                      {titleCase(f.classification)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="tabular-nums">
                        {Math.round(f.confidence * 100)}%
                      </span>{" "}
                      <Badge label={f.confidence_band} variant={f.confidence_band} />
                    </td>
                    <td className="px-4 py-2.5 text-muted">
                      {titleCase(f.detection_method)}
                    </td>
                    <td className="px-4 py-2.5">
                      {f.needs_review ? (
                        <Badge label="NEEDS_REVIEW" />
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                )}
              />
            </Table>
          )}
        </Panel>
      )}

      {tab === "flows" && (
        <Panel>
          {flows.isLoading ? (
            <Spinner />
          ) : !flows.data || flows.data.length === 0 ? (
            <EmptyState message="No data flows recorded for this asset." />
          ) : (
            <Table>
              <THead>
                <tr>
                  <TH>Flow Type</TH>
                  <TH>Purpose</TH>
                  <TH>Personal Data</TH>
                  <TH>Cross-border</TH>
                  <TH>Categories</TH>
                </tr>
              </THead>
              <TBodyRows
                rows={flows.data}
                render={(f) => (
                  <tr key={f.id} className="border-b border-border/60">
                    <td className="px-4 py-2.5">{titleCase(f.flow_type)}</td>
                    <td className="px-4 py-2.5 text-muted">{f.purpose || "—"}</td>
                    <td className="px-4 py-2.5">
                      {f.contains_personal_data ? (
                        <span className="text-medium">Yes</span>
                      ) : (
                        <span className="text-muted">No</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {f.cross_border ? (
                        <Badge label="Cross-border" variant="HIGH" />
                      ) : (
                        <span className="text-muted">No</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-muted">
                      {f.categories || "—"}
                    </td>
                  </tr>
                )}
              />
            </Table>
          )}
        </Panel>
      )}

      {tab === "controls" && (
        <Panel>
          {controls.isLoading ? (
            <Spinner />
          ) : !controls.data || controls.data.length === 0 ? (
            <EmptyState message="No controls scoped to this asset." />
          ) : (
            <Table>
              <THead>
                <tr>
                  <TH>Code</TH>
                  <TH>Control</TH>
                  <TH>Applicable</TH>
                  <TH>Reason</TH>
                </tr>
              </THead>
              <TBodyRows
                rows={controls.data}
                render={(c) => (
                  <tr key={c.control_id} className="border-b border-border/60">
                    <td className="px-4 py-2.5 font-mono text-xs">
                      <Link
                        href={`/controls/${c.control_id}`}
                        className="text-accent hover:underline"
                      >
                        {c.code}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">{c.title}</td>
                    <td className="px-4 py-2.5">
                      {c.applicable ? (
                        <span className="text-pass">Yes</span>
                      ) : (
                        <span className="text-muted">No</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-muted">{c.reason || "—"}</td>
                  </tr>
                )}
              />
            </Table>
          )}
        </Panel>
      )}
    </>
  );
}
