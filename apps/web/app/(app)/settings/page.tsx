"use client";

import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Field } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import { useOrganization } from "@/lib/queries";

export default function SettingsOrganizationPage() {
  const org = useOrganization();

  return (
    <div className="space-y-4">
      <Panel title="Organization">
        {org.isLoading ? (
          <Spinner />
        ) : org.isError || !org.data ? (
          <ErrorState message="Could not load organization settings." />
        ) : (
          <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-3">
            <Field label="Name" value={org.data.name} />
            <Field label="Slug" value={org.data.slug} />
            <Field label="Industry" value={org.data.industry || "—"} />
            <Field label="Country" value={org.data.country} />
            <Field label="Plan" value={titleCase(org.data.plan)} />
            <Field
              label="Assessment date"
              value={formatDate(org.data.assessment_date)}
            />
          </div>
        )}
      </Panel>

      <Panel title="Assessment date">
        <div className="p-4 text-sm text-muted">
          The effective-date engine uses the organization assessment date (not the
          current wall-clock date) to decide whether a control is in force. This
          keeps assessments reproducible and lets you evaluate posture against a
          fixed point in time.
        </div>
      </Panel>
    </div>
  );
}
