"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, Field, Input, PageHeader } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useCreateCampaign, useCampaigns, useRegulations } from "@/lib/queries";
import type { Campaign } from "@/lib/types";
import Link from "next/link";
import { useState } from "react";

function coverageTone(pct: number): string {
  if (pct >= 90) return "text-pass";
  if (pct >= 70) return "text-upcoming";
  return "text-danger";
}

export default function CampaignsPage() {
  const campaigns = useCampaigns();
  const regulations = useRegulations();
  const create = useCreateCampaign();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scope, setScope] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function toggleScope(id: string) {
    setScope((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function submit() {
    setError(null);
    if (!name.trim()) {
      setError("A campaign needs a name.");
      return;
    }
    try {
      await create.mutateAsync({
        name: name.trim(),
        description: description || undefined,
        scope_regulation_ids: scope.length ? scope : undefined,
      });
      setOpen(false);
      setName("");
      setDescription("");
      setScope([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the campaign.");
    }
  }

  return (
    <>
      <PageHeader
        title="Audit campaigns"
        description="Run a scoped, point-in-time assessment across one or more frameworks. Completed campaigns are frozen as an audit record you can compare over time."
        actions={
          <Button variant="primary" onClick={() => setOpen(true)}>
            New campaign
          </Button>
        }
      />

      <Panel title="Campaigns">
        {campaigns.isLoading ? (
          <Spinner />
        ) : campaigns.isError ? (
          <ErrorState message="Could not load campaigns." />
        ) : !campaigns.data || campaigns.data.length === 0 ? (
          <EmptyState message="No campaigns yet. Create one to run a scoped assessment." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>Status</TH>
                <TH>Coverage</TH>
                <TH>Controls</TH>
                <TH>Assessment date</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={campaigns.data}
              render={(c: Campaign) => (
                <tr key={c.id} className="border-b border-border/60 align-top">
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/campaigns/${c.id}`}
                      className="text-sm font-medium text-accent hover:underline"
                    >
                      {c.name}
                    </Link>
                    {c.description && <div className="text-xs text-muted">{c.description}</div>}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={c.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    {c.summary ? (
                      <span className={coverageTone(c.summary.coverage)}>
                        {c.summary.coverage}%
                      </span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs tabular-nums text-muted">
                    {c.summary ? `${c.summary.applicable}/${c.summary.total}` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted">
                    {c.assessment_date ? formatDate(c.assessment_date) : "—"}
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <Drawer open={open} onClose={() => setOpen(false)} title="New audit campaign">
        <div className="space-y-4">
          <Field
            label="Name"
            value={
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Q3 2026 DPDP review"
                className="w-full"
              />
            }
          />
          <Field
            label="Description (optional)"
            value={
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Purpose or scope notes"
                className="w-full"
              />
            }
          />
          <div>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted">
              Frameworks in scope
            </div>
            <p className="mb-2 text-xs text-muted">
              Leave all unchecked to assess every framework.
            </p>
            <div className="space-y-1.5">
              {(regulations.data || []).map((reg) => (
                <label key={reg.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scope.includes(reg.id)}
                    onChange={() => toggleScope(reg.id)}
                    className="h-3.5 w-3.5"
                  />
                  {reg.name}
                </label>
              ))}
            </div>
          </div>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submit} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create campaign"}
            </Button>
          </div>
        </div>
      </Drawer>
    </>
  );
}
