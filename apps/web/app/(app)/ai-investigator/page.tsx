"use client";

import { Badge } from "@/components/badge";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { PageHeader } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { useAiMode, useInvestigations } from "@/lib/queries";
import { AlertCircle, Sparkles } from "lucide-react";
import Link from "next/link";

export default function AiInvestigatorPage() {
  const { data: mode } = useAiMode();
  const investigations = useInvestigations();

  return (
    <>
      <PageHeader
        title="AI Investigator"
        description="Advisory analysis of findings. The deterministic engine always decides; AI only assists."
        actions={
          mode && (
            <span className="rounded border border-border bg-panel-2 px-2.5 py-1 text-xs text-muted">
              Mode: {titleCase(mode.ai_mode)}
              {mode.model ? ` · ${mode.model}` : ""}
            </span>
          )
        }
      />

      <div className="mb-4 flex items-start gap-2 rounded-lg border border-upcoming/40 bg-upcoming/10 px-4 py-3 text-sm text-upcoming">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          AI investigations are advisory only. Raw personal data is never sent to
          the model — inputs are sanitized and redacted. Recommendations do not
          constitute legal advice.
        </div>
      </div>

      <Panel
        title={
          investigations.data
            ? `${investigations.data.length} investigations`
            : "Investigations"
        }
      >
        {investigations.isLoading ? (
          <Spinner />
        ) : investigations.isError ? (
          <ErrorState message="Could not load investigations." />
        ) : !investigations.data || investigations.data.length === 0 ? (
          <EmptyState message="No investigations yet. Run AI Investigate from a finding to generate one." />
        ) : (
          <div className="divide-y divide-border">
            {investigations.data.map((inv) => (
              <div key={inv.id} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-upcoming" />
                    <Badge
                      label={inv.mode}
                      className="bg-upcoming/15 text-upcoming border-upcoming/30"
                    />
                    {inv.legal_review_required && (
                      <span className="text-xs text-medium">Legal review</span>
                    )}
                  </div>
                  {inv.finding_id && (
                    <Link
                      href={`/findings/${inv.finding_id}`}
                      className="text-xs text-accent hover:underline"
                    >
                      View finding
                    </Link>
                  )}
                </div>
                {inv.summary && (
                  <p className="mt-2 text-sm leading-relaxed">{inv.summary}</p>
                )}
                <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-muted">
                  {inv.input_sanitized && (
                    <span className="rounded border border-border bg-panel-2 px-2 py-0.5">
                      {inv.input_sanitized_notice || "AI input sanitized"}
                    </span>
                  )}
                  <span className="rounded border border-border bg-panel-2 px-2 py-0.5">
                    {inv.raw_pii_excluded_notice || "Raw personal data excluded"}
                  </span>
                  {inv.model && (
                    <span className="rounded border border-border bg-panel-2 px-2 py-0.5">
                      {inv.model}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}
