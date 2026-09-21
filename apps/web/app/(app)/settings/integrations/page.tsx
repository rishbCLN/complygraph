"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, Field, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  useCreateWebhook,
  useDeleteWebhook,
  useIntegrationStatus,
  useRotateWebhookSecret,
  useTestWebhook,
  useUpdateWebhook,
  useWebhookDeliveries,
  useWebhooks,
} from "@/lib/queries";
import type { WebhookEndpoint, WebhookWithSecret } from "@/lib/types";
import { Copy, Send, Trash2 } from "lucide-react";
import { useState } from "react";

export default function SettingsIntegrationsPage() {
  const status = useIntegrationStatus();
  const webhooks = useWebhooks();
  const createMut = useCreateWebhook();
  const events = status.data?.webhook_events ?? [];

  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [newSecret, setNewSecret] = useState<WebhookWithSecret | null>(null);
  const [openDeliveries, setOpenDeliveries] = useState<WebhookEndpoint | null>(null);

  function resetForm() {
    setName("");
    setUrl("");
    setSelected([]);
    setFormError(null);
  }

  function toggleEvent(evt: string) {
    setSelected((prev) =>
      prev.includes(evt) ? prev.filter((e) => e !== evt) : [...prev, evt],
    );
  }

  function submitCreate() {
    setFormError(null);
    if (!name.trim() || !url.trim()) {
      setFormError("Name and URL are required.");
      return;
    }
    createMut.mutate(
      { name: name.trim(), url: url.trim(), events: selected },
      {
        onSuccess: (data) => {
          setNewSecret(data);
          setCreating(false);
          resetForm();
        },
        onError: (err) =>
          setFormError(
            err instanceof ApiError ? err.message : "Could not create endpoint.",
          ),
      },
    );
  }

  return (
    <div className="space-y-4">
      {/* Provider status ------------------------------------------------- */}
      <Panel title="Integration status">
        {status.isLoading ? (
          <Spinner />
        ) : status.isError ? (
          <ErrorState message="Could not load integration status." />
        ) : (
          <div className="divide-y divide-border">
            {status.data?.integrations.map((it) => (
              <div
                key={it.name}
                className="flex items-start justify-between gap-4 px-4 py-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium capitalize">{it.name}</span>
                    <Badge
                      label={it.configured ? "Configured" : "Dormant"}
                      variant={it.configured ? "PASS" : "UNKNOWN"}
                    />
                  </div>
                  <p className="mt-0.5 text-xs text-muted">{it.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Webhooks -------------------------------------------------------- */}
      <Panel
        title="Outbound webhooks"
        actions={
          <Button size="sm" variant="primary" onClick={() => setCreating(true)}>
            New endpoint
          </Button>
        }
      >
        {webhooks.isLoading ? (
          <Spinner />
        ) : webhooks.isError ? (
          <ErrorState message="Could not load webhook endpoints." />
        ) : !webhooks.data || webhooks.data.length === 0 ? (
          <EmptyState message="No webhook endpoints yet. Create one to stream domain events to a SIEM or automation." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Name</TH>
                <TH>URL</TH>
                <TH>Events</TH>
                <TH>Last status</TH>
                <TH>Last delivery</TH>
                <TH></TH>
              </tr>
            </THead>
            <TBodyRows
              rows={webhooks.data}
              render={(ep) => (
                <WebhookRow
                  key={ep.id}
                  ep={ep}
                  onViewDeliveries={() => setOpenDeliveries(ep)}
                  onRotated={(s) => setNewSecret(s)}
                />
              )}
            />
          </Table>
        )}
      </Panel>

      {/* Create drawer --------------------------------------------------- */}
      <Drawer
        open={creating}
        onClose={() => {
          setCreating(false);
          resetForm();
        }}
        title="New webhook endpoint"
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted">Name</label>
            <Input
              className="w-full"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="SIEM receiver"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted">
              Payload URL
            </label>
            <Input
              className="w-full"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/hooks/complygraph"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted">
              Subscribed events
            </label>
            <div className="grid grid-cols-1 gap-1.5">
              {events.map((evt) => (
                <label
                  key={evt}
                  className="flex items-center gap-2 rounded border border-border bg-panel-2 px-2.5 py-1.5 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(evt)}
                    onChange={() => toggleEvent(evt)}
                  />
                  <span className="font-mono text-xs">{evt}</span>
                </label>
              ))}
              {events.length === 0 && (
                <p className="text-xs text-muted">No event types available.</p>
              )}
            </div>
          </div>
          {formError && (
            <div className="rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail">
              {formError}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setCreating(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={submitCreate}
              disabled={createMut.isPending}
            >
              {createMut.isPending ? "Creating…" : "Create endpoint"}
            </Button>
          </div>
        </div>
      </Drawer>

      {/* Secret reveal (once) ------------------------------------------- */}
      <Drawer
        open={!!newSecret}
        onClose={() => setNewSecret(null)}
        title="Signing secret"
      >
        {newSecret && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Copy this secret now. It is shown only once and is used to verify the{" "}
              <span className="font-mono">X-ComplyGraph-Signature</span> header on
              each delivery.
            </p>
            <div className="flex items-center gap-2 rounded border border-border bg-panel-2 px-3 py-2">
              <code className="flex-1 break-all text-xs">{newSecret.secret}</code>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => navigator.clipboard?.writeText(newSecret.secret)}
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="flex justify-end">
              <Button variant="primary" onClick={() => setNewSecret(null)}>
                Done
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Delivery history ------------------------------------------------ */}
      <Drawer
        open={!!openDeliveries}
        onClose={() => setOpenDeliveries(null)}
        title={openDeliveries ? `Deliveries — ${openDeliveries.name}` : "Deliveries"}
        width="max-w-2xl"
      >
        {openDeliveries && <DeliveriesView endpointId={openDeliveries.id} />}
      </Drawer>
    </div>
  );
}

function WebhookRow({
  ep,
  onViewDeliveries,
  onRotated,
}: {
  ep: WebhookEndpoint;
  onViewDeliveries: () => void;
  onRotated: (s: WebhookWithSecret) => void;
}) {
  const testMut = useTestWebhook();
  const deleteMut = useDeleteWebhook();
  const updateMut = useUpdateWebhook();
  const rotateMut = useRotateWebhookSecret();
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <tr className="border-b border-border/60">
      <td className="px-4 py-2.5 font-medium">
        {ep.name}
        {!ep.enabled && (
          <span className="ml-2 text-xs text-muted">(disabled)</span>
        )}
      </td>
      <td className="max-w-[220px] truncate px-4 py-2.5 font-mono text-xs text-muted">
        {ep.url}
      </td>
      <td className="px-4 py-2.5 text-xs text-muted">
        {ep.events.length === 0 ? "—" : `${ep.events.length} event(s)`}
      </td>
      <td className="px-4 py-2.5">
        {ep.last_status ? (
          <Badge
            label={ep.last_status}
            variant={ep.last_status === "delivered" ? "PASS" : "FAIL"}
          />
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>
      <td className="px-4 py-2.5 text-muted">{formatDateTime(ep.last_delivery_at)}</td>
      <td className="px-4 py-2.5">
        <div className="flex items-center justify-end gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => testMut.mutate(ep.id)}
            disabled={testMut.isPending}
            title="Send test event"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" variant="ghost" onClick={onViewDeliveries}>
            Deliveries
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              updateMut.mutate({ id: ep.id, body: { enabled: !ep.enabled } })
            }
            disabled={updateMut.isPending}
          >
            {ep.enabled ? "Disable" : "Enable"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              rotateMut.mutate(ep.id, { onSuccess: (s) => onRotated(s) })
            }
            disabled={rotateMut.isPending}
          >
            Rotate secret
          </Button>
          {confirmDelete ? (
            <>
              <Button
                size="sm"
                variant="danger"
                onClick={() => deleteMut.mutate(ep.id)}
                disabled={deleteMut.isPending}
              >
                Confirm
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmDelete(false)}
              >
                No
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setConfirmDelete(true)}
              title="Delete endpoint"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

function DeliveriesView({ endpointId }: { endpointId: string }) {
  const deliveries = useWebhookDeliveries(endpointId);

  if (deliveries.isLoading) return <Spinner />;
  if (deliveries.isError)
    return <ErrorState message="Could not load delivery history." />;
  if (!deliveries.data || deliveries.data.length === 0)
    return <EmptyState message="No deliveries recorded yet." />;

  return (
    <div className="space-y-2">
      {deliveries.data.map((d) => (
        <div
          key={d.id}
          className="rounded border border-border bg-panel-2 p-3 text-sm"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs">{d.event}</span>
            <Badge
              label={d.status}
              variant={d.status === "delivered" ? "PASS" : "FAIL"}
            />
          </div>
          <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-muted">
            <Field
              label="HTTP"
              value={d.response_code !== null ? String(d.response_code) : "—"}
            />
            <Field label="Attempts" value={String(d.attempts)} />
            <Field label="Sent" value={formatDateTime(d.created_at)} />
            <Field label="Completed" value={formatDateTime(d.completed_at)} />
          </div>
          {d.detail && (
            <p className="mt-2 break-all text-xs text-muted">{d.detail}</p>
          )}
        </div>
      ))}
    </div>
  );
}
