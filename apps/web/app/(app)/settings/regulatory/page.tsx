"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Table, TBodyRows, TH, THead } from "@/components/table";
import { Drawer, PageHeader, Select } from "@/components/ui";
import { formatDate } from "@/lib/format";
import {
  useDeletePackMutation,
  useImportPackMutation,
  useRegulations,
} from "@/lib/queries";
import { Trash2 } from "lucide-react";
import { useState } from "react";

const SAMPLE = `pack:
  name: "My Internal Security Standard"
  jurisdiction: "Internal"
  version: "1.0"
  legal_status: "INTERNAL_POLICY"
  source_document: "InfoSec Policy v1.0"
obligations:
  - code: "OBL-1"
    title: "Access governance"
    description: "Least-privilege access to production data."
    legal_status: "INTERNAL_POLICY"
    controls:
      - code: "AC-001"
        title: "MFA enforced for production access"
        category: "SECURITY"
        severity: "HIGH"
      - code: "AC-002"
        title: "Quarterly access review"
        category: "SECURITY"
        severity: "MEDIUM"
`;

export default function SettingsRegulatoryPage() {
  const regulations = useRegulations();
  const importPack = useImportPackMutation();
  const deletePack = useDeletePackMutation();

  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState<"yaml" | "json">("yaml");
  const [content, setContent] = useState(SAMPLE);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      await importPack.mutateAsync({ format, content });
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed.");
    }
  }

  return (
    <>
      <PageHeader
        title="Regulatory scope"
        description="Shipped frameworks plus your organization's own custom packs. Custom packs are private to your organization."
        actions={
          <Button variant="primary" onClick={() => setOpen(true)}>
            Import custom pack
          </Button>
        }
      />
      <Panel title="Frameworks">
        {regulations.isLoading ? (
          <Spinner />
        ) : regulations.isError ? (
          <ErrorState message="Could not load regulations." />
        ) : !regulations.data || regulations.data.length === 0 ? (
          <EmptyState message="No regulations configured." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Regulation</TH>
                <TH>Jurisdiction</TH>
                <TH>Version</TH>
                <TH>Origin</TH>
                <TH>Obligations</TH>
                <TH>Status</TH>
                <TH> </TH>
              </tr>
            </THead>
            <TBodyRows
              rows={regulations.data}
              render={(r) => (
                <tr key={r.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{r.name}</td>
                  <td className="px-4 py-2.5 text-muted">{r.jurisdiction}</td>
                  <td className="px-4 py-2.5 text-muted">{r.version || "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={r.is_custom ? "CUSTOM" : "SYSTEM"} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">
                    {r.obligation_count}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge label={r.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    {r.is_custom && (
                      <button
                        onClick={() => deletePack.mutate(r.id)}
                        disabled={deletePack.isPending}
                        className="text-muted hover:text-danger"
                        title="Delete custom pack"
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

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title="Import custom regulatory pack"
        width="max-w-2xl"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Format</span>
            <Select
              value={format}
              onChange={(e) => setFormat(e.target.value as "yaml" | "json")}
            >
              <option value="yaml">YAML</option>
              <option value="json">JSON</option>
            </Select>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
            className="h-80 w-full rounded border border-border bg-panel-2 p-3 font-mono text-xs outline-none focus:border-accent"
          />
          <p className="text-xs text-muted">
            Every control code must be unique across all frameworks. Unknown
            evaluator keys fall back to a generic evidence check. legal_status must
            be a recognized value (e.g. INTERNAL_POLICY, BEST_PRACTICE).
          </p>
          {error && <div className="text-sm text-danger">{error}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={submit}
              disabled={importPack.isPending}
            >
              {importPack.isPending ? "Importing…" : "Import pack"}
            </Button>
          </div>
        </div>
      </Drawer>
    </>
  );
}
