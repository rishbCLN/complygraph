"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, MetricCard, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, Field, Input, PageHeader, Tabs } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import {
  useArchivePurpose,
  useConsentEvents,
  useConsentNotices,
  useConsentRecords,
  useConsentSummary,
  useConsentPurposes,
  useCreateNotice,
  useCreatePurpose,
  usePublishNotice,
} from "@/lib/queries";
import type { ConsentEvent, ConsentNotice, ConsentPurpose } from "@/lib/types";
import { useState } from "react";

export default function ConsentPage() {
  const [tab, setTab] = useState("purposes");
  const summary = useConsentSummary();

  return (
    <>
      <PageHeader
        title="Consent"
        description="Manage the purpose catalogue, versioned privacy notices, and the append-only consent ledger. Data principals self-serve through the Privacy Center portal."
      />

      {summary.data && (
        <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-5">
          <MetricCard label="Active purposes" value={summary.data.active_purposes} />
          <MetricCard label="Consents granted" value={summary.data.total_granted} tone="good" />
          <MetricCard label="Withdrawn" value={summary.data.total_withdrawn} tone="warn" />
          <MetricCard label="Principals" value={summary.data.distinct_principals} />
          <MetricCard
            label="Notice version"
            value={summary.data.current_notice_version ?? "None"}
            tone={summary.data.current_notice_version ? "default" : "critical"}
          />
        </div>
      )}

      <Tabs
        tabs={[
          { key: "purposes", label: "Purposes" },
          { key: "notices", label: "Notices" },
          { key: "ledger", label: "Ledger" },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="mt-4">
        {tab === "purposes" && <PurposesTab />}
        {tab === "notices" && <NoticesTab />}
        {tab === "ledger" && <LedgerTab />}
      </div>
    </>
  );
}

function PurposesTab() {
  const purposes = useConsentPurposes();
  const create = useCreatePurpose();
  const archive = useArchivePurpose();

  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [lawfulBasis, setLawfulBasis] = useState("Consent");
  const [requiresConsent, setRequiresConsent] = useState(true);
  const [isSensitive, setIsSensitive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (!code.trim() || !name.trim()) {
      setError("Code and name are required.");
      return;
    }
    try {
      await create.mutateAsync({
        code: code.trim(),
        name: name.trim(),
        description: description || undefined,
        lawful_basis: lawfulBasis || "Consent",
        requires_consent: requiresConsent,
        is_sensitive: isSensitive,
      });
      setOpen(false);
      setCode("");
      setName("");
      setDescription("");
      setRequiresConsent(true);
      setIsSensitive(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create purpose.");
    }
  }

  return (
    <Panel
      title="Purpose catalogue"
      actions={
        <Button variant="primary" onClick={() => setOpen(true)}>
          New purpose
        </Button>
      }
    >
      {purposes.isLoading ? (
        <Spinner />
      ) : purposes.isError ? (
        <ErrorState message="Could not load purposes." />
      ) : !purposes.data || purposes.data.length === 0 ? (
        <EmptyState message="No purposes yet. Add the purposes you process personal data for." />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>Purpose</TH>
              <TH>Lawful basis</TH>
              <TH>Consent</TH>
              <TH>Status</TH>
              <TH></TH>
            </tr>
          </THead>
          <TBodyRows
            rows={purposes.data}
            render={(p: ConsentPurpose) => (
              <tr key={p.id} className="border-b border-border/60 align-top">
                <td className="px-4 py-2.5">
                  <div className="text-sm font-medium">{p.name}</div>
                  <div className="font-mono text-[11px] text-muted">{p.code}</div>
                  {p.is_sensitive && (
                    <Badge label="SENSITIVE" className="mt-1" />
                  )}
                </td>
                <td className="px-4 py-2.5 text-sm text-muted">{p.lawful_basis}</td>
                <td className="px-4 py-2.5 text-xs text-muted">
                  {p.requires_consent ? "Required" : "Not required"}
                </td>
                <td className="px-4 py-2.5">
                  <Badge label={p.status} />
                </td>
                <td className="px-4 py-2.5 text-right">
                  {p.status === "ACTIVE" && (
                    <Button
                      variant="ghost"
                      onClick={() => archive.mutate(p.id)}
                      disabled={archive.isPending}
                    >
                      Archive
                    </Button>
                  )}
                </td>
              </tr>
            )}
          />
        </Table>
      )}

      <Drawer open={open} onClose={() => setOpen(false)} title="New consent purpose">
        <div className="space-y-4">
          <Field
            label="Code"
            value={
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. marketing"
                className="w-full"
              />
            }
          />
          <Field
            label="Name"
            value={
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Marketing communications"
                className="w-full"
              />
            }
          />
          <Field
            label="Description"
            value={
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this purpose covers"
                className="w-full"
              />
            }
          />
          <Field
            label="Lawful basis"
            value={
              <Input
                value={lawfulBasis}
                onChange={(e) => setLawfulBasis(e.target.value)}
                className="w-full"
              />
            }
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={requiresConsent}
              onChange={(e) => setRequiresConsent(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            Requires consent (uncheck for contract/legal-obligation purposes)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isSensitive}
              onChange={(e) => setIsSensitive(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            Involves sensitive personal data
          </label>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submit} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create purpose"}
            </Button>
          </div>
        </div>
      </Drawer>
    </Panel>
  );
}

function NoticesTab() {
  const notices = useConsentNotices();
  const create = useCreateNotice();
  const publish = usePublishNotice();

  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(shouldPublish: boolean) {
    setError(null);
    if (!title.trim() || !body.trim()) {
      setError("Title and body are required.");
      return;
    }
    try {
      await create.mutateAsync({ title: title.trim(), body: body.trim(), publish: shouldPublish });
      setOpen(false);
      setTitle("");
      setBody("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create notice.");
    }
  }

  return (
    <Panel
      title="Privacy notices"
      actions={
        <Button variant="primary" onClick={() => setOpen(true)}>
          New version
        </Button>
      }
    >
      {notices.isLoading ? (
        <Spinner />
      ) : notices.isError ? (
        <ErrorState message="Could not load notices." />
      ) : !notices.data || notices.data.length === 0 ? (
        <EmptyState message="No notice published yet. Publish one so the Privacy Center can display it." />
      ) : (
        <div className="divide-y divide-border">
          {notices.data.map((n: ConsentNotice) => (
            <div key={n.id} className="flex items-start justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{n.title}</span>
                  <span className="text-xs text-muted">v{n.version}</span>
                  {n.is_current && <Badge label="CURRENT" />}
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-muted">{n.body}</p>
                {n.published_at && (
                  <div className="mt-1 text-[11px] text-muted">
                    Published {formatDateTime(n.published_at)}
                  </div>
                )}
              </div>
              {!n.is_current && (
                <Button
                  variant="secondary"
                  onClick={() => publish.mutate(n.id)}
                  disabled={publish.isPending}
                >
                  Publish
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <Drawer open={open} onClose={() => setOpen(false)} title="New notice version">
        <div className="space-y-4">
          <Field
            label="Title"
            value={
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full"
              />
            }
          />
          <div>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted">
              Body
            </div>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className="w-full rounded border border-border bg-panel-2 px-2.5 py-1.5 text-sm outline-none focus:border-accent"
              placeholder="The privacy notice shown to data principals in the portal."
            />
          </div>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="secondary" onClick={() => submit(false)} disabled={create.isPending}>
              Save draft
            </Button>
            <Button variant="primary" onClick={() => submit(true)} disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Save & publish"}
            </Button>
          </div>
        </div>
      </Drawer>
    </Panel>
  );
}

function LedgerTab() {
  const [principal, setPrincipal] = useState("");
  const events = useConsentEvents(principal ? { principal } : {});
  const records = useConsentRecords();

  return (
    <div className="space-y-4">
      <Panel title="Current consent records">
        {records.isLoading ? (
          <Spinner />
        ) : !records.data || records.data.length === 0 ? (
          <EmptyState message="No consent records yet." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Principal</TH>
                <TH>Status</TH>
                <TH>Method</TH>
                <TH>Verified</TH>
                <TH>Updated</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={records.data}
              render={(r) => (
                <tr key={r.id} className="border-b border-border/60">
                  <td className="px-4 py-2 font-mono text-xs">{r.principal_identifier}</td>
                  <td className="px-4 py-2">
                    <Badge label={r.status} />
                  </td>
                  <td className="px-4 py-2 text-xs text-muted">{r.method}</td>
                  <td className="px-4 py-2 text-xs text-muted">
                    {r.verified ? "Verified" : "Self-asserted"}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted">
                    {formatDateTime(r.granted_at || r.withdrawn_at)}
                  </td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>

      <Panel
        title="Consent ledger (append-only)"
        actions={
          <Input
            value={principal}
            onChange={(e) => setPrincipal(e.target.value)}
            placeholder="Filter by principal"
            className="w-56"
          />
        }
      >
        {events.isLoading ? (
          <Spinner />
        ) : !events.data || events.data.length === 0 ? (
          <EmptyState message="No consent events recorded." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>When</TH>
                <TH>Principal</TH>
                <TH>Purpose</TH>
                <TH>Event</TH>
                <TH>Source</TH>
              </tr>
            </THead>
            <TBodyRows
              rows={events.data}
              render={(e: ConsentEvent) => (
                <tr key={e.id} className="border-b border-border/60">
                  <td className="px-4 py-2 text-xs text-muted">{formatDateTime(e.created_at)}</td>
                  <td className="px-4 py-2 font-mono text-xs">{e.principal_identifier}</td>
                  <td className="px-4 py-2 text-sm">{e.purpose_name}</td>
                  <td className="px-4 py-2">
                    <Badge label={e.event_type} />
                  </td>
                  <td className="px-4 py-2 text-xs text-muted">{e.source}</td>
                </tr>
              )}
            />
          </Table>
        )}
      </Panel>
    </div>
  );
}
