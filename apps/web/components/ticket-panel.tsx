"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, Panel, Spinner } from "@/components/panel";
import { Select } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCreateTicket, useMe, useTickets } from "@/lib/queries";
import { ExternalLink } from "lucide-react";
import { useState } from "react";

// Create + list external tickets (Jira / ServiceNow) for a finding or risk.
// Providers are only usable when configured server-side; creation returns a
// 400 (IntegrationNotConfigured) otherwise, which we surface inline.
export function TicketPanel({
  entityType,
  entityId,
  defaultSummary,
}: {
  entityType: "finding" | "risk";
  entityId: string;
  defaultSummary?: string;
}) {
  const me = useMe();
  const tickets = useTickets({ entity_type: entityType, entity_id: entityId });
  const createMut = useCreateTicket();
  const canCreate = me.data?.capabilities?.includes("create_ticket") ?? false;

  const [provider, setProvider] = useState("JIRA");
  const [error, setError] = useState<string | null>(null);

  function submit() {
    setError(null);
    createMut.mutate(
      {
        provider,
        entity_type: entityType,
        entity_id: entityId,
        summary: defaultSummary,
      },
      {
        onError: (err) =>
          setError(
            err instanceof ApiError
              ? err.message
              : "Could not create the ticket.",
          ),
      },
    );
  }

  return (
    <Panel
      title="External tickets"
      actions={
        canCreate ? (
          <div className="flex items-center gap-2">
            <Select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="text-xs"
            >
              <option value="JIRA">Jira</option>
              <option value="SERVICENOW">ServiceNow</option>
            </Select>
            <Button
              size="sm"
              variant="primary"
              onClick={submit}
              disabled={createMut.isPending}
            >
              {createMut.isPending ? "Creating…" : "Create ticket"}
            </Button>
          </div>
        ) : undefined
      }
    >
      {error && (
        <div className="m-3 rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail">
          {error}
        </div>
      )}
      {tickets.isLoading ? (
        <Spinner />
      ) : !tickets.data || tickets.data.length === 0 ? (
        <EmptyState message="No tickets raised for this item." />
      ) : (
        <div className="divide-y divide-border">
          {tickets.data.map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
            >
              <div className="flex items-center gap-2">
                <Badge label={t.provider} />
                <span className="font-medium">
                  {t.external_key || "(pending)"}
                </span>
                <span className="text-muted">{t.status}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted">
                <span>{formatDateTime(t.created_at)}</span>
                {t.external_url && (
                  <a
                    href={t.external_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-accent hover:underline"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
