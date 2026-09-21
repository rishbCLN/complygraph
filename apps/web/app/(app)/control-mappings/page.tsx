"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, Field, Input, PageHeader, Select } from "@/components/ui";
import {
  useControlMappingsList,
  useControls,
  useCreateControlMapping,
  useDeleteControlMapping,
} from "@/lib/queries";
import { ArrowRight, Trash2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

const RELATIONS = ["EQUIVALENT", "SUPERSET", "SUBSET", "RELATED"];

export default function ControlMappingsPage() {
  const mappings = useControlMappingsList();
  const controls = useControls();
  const create = useCreateControlMapping();
  const remove = useDeleteControlMapping();

  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [relation, setRelation] = useState("RELATED");
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState<string | null>(null);

  const controlOptions = useMemo(
    () => (controls.data || []).slice().sort((a, b) => a.code.localeCompare(b.code)),
    [controls.data],
  );

  function reset() {
    setSource("");
    setTarget("");
    setRelation("RELATED");
    setRationale("");
    setError(null);
  }

  async function submit() {
    setError(null);
    if (!source || !target) {
      setError("Select both a source and a target control.");
      return;
    }
    try {
      await create.mutateAsync({
        source_control_id: source,
        target_control_id: target,
        relation_type: relation,
        rationale: rationale || undefined,
      });
      setOpen(false);
      reset();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create mapping.");
    }
  }

  return (
    <>
      <PageHeader
        title="Control mapping explorer"
        description="Cross-framework equivalences. Evidence on a source control can be reused for a target control it covers (EQUIVALENT / SUPERSET), subject to review."
        actions={<Button variant="primary" onClick={() => setOpen(true)}>New mapping</Button>}
      />

      <Panel title={mappings.data ? `${mappings.data.length} mappings` : "Mappings"}>
        {mappings.isLoading ? (
          <Spinner />
        ) : mappings.isError ? (
          <ErrorState message="Could not load control mappings." />
        ) : !mappings.data || mappings.data.length === 0 ? (
          <EmptyState message="No cross-framework mappings yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Source control</TH>
                <TH>Relation</TH>
                <TH>Target control</TH>
                <TH>Rationale</TH>
                <TH>Origin</TH>
                <TH> </TH>
              </tr>
            </THead>
            <TBodyRows
              rows={mappings.data}
              render={(m) => (
                <tr key={m.id} className="border-b border-border/60 align-top">
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/controls/${m.source.id}`}
                      className="font-mono text-xs text-accent hover:underline"
                    >
                      {m.source.code}
                    </Link>
                    <div className="text-xs text-muted">
                      {m.source.regulation_name || "—"}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-1">
                      <Badge label={m.relation_type} />
                      <ArrowRight className="h-3 w-3 text-muted" />
                    </span>
                    <div className="mt-1 text-xs tabular-nums text-muted">
                      {Math.round(m.confidence * 100)}%
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/controls/${m.target.id}`}
                      className="font-mono text-xs text-accent hover:underline"
                    >
                      {m.target.code}
                    </Link>
                    <div className="text-xs text-muted">
                      {m.target.regulation_name || "—"}
                    </div>
                  </td>
                  <td className="max-w-xs px-4 py-2.5 text-xs text-muted">
                    {m.rationale || "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={m.system ? "SYSTEM" : "ORG"} />
                  </td>
                  <td className="px-4 py-2.5">
                    {!m.system && (
                      <button
                        onClick={() => remove.mutate(m.id)}
                        disabled={remove.isPending}
                        className="text-muted hover:text-danger"
                        title="Delete mapping"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <Drawer open={open} onClose={() => setOpen(false)} title="New control mapping">
        <div className="space-y-4">
          <Field
            label="Source control"
            value={
              <Select value={source} onChange={(e) => setSource(e.target.value)} className="w-full">
                <option value="">Select a control…</option>
                {controlOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.title}
                  </option>
                ))}
              </Select>
            }
          />
          <Field
            label="Relation (source → target)"
            value={
              <Select value={relation} onChange={(e) => setRelation(e.target.value)} className="w-full">
                {RELATIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            }
          />
          <Field
            label="Target control"
            value={
              <Select value={target} onChange={(e) => setTarget(e.target.value)} className="w-full">
                <option value="">Select a control…</option>
                {controlOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.title}
                  </option>
                ))}
              </Select>
            }
          />
          <Field
            label="Rationale (optional)"
            value={
              <Input
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Why these controls relate…"
                className="w-full"
              />
            }
          />
          <p className="text-xs text-muted">
            EQUIVALENT / SUPERSET assert that satisfying the source can satisfy the
            target and enable evidence reuse (with review). SUBSET / RELATED are
            informational only.
          </p>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submit} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create mapping"}
            </Button>
          </div>
        </div>
      </Drawer>
    </>
  );
}
