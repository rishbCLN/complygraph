"use client";

import { cn } from "@/lib/format";
import { Handle, Position } from "@xyflow/react";
import { AppWindow, Boxes, Database, FileText, Server } from "lucide-react";
import { memo } from "react";

const KIND_META: Record<
  string,
  { icon: typeof Database; ring: string; label: string }
> = {
  DATABASE: { icon: Database, ring: "border-accent/60", label: "Database" },
  DATASET: { icon: Server, ring: "border-accent/60", label: "Dataset" },
  FILE: { icon: FileText, ring: "border-medium/60", label: "File" },
  APPLICATION: { icon: AppWindow, ring: "border-low/60", label: "Application" },
  VENDOR: { icon: Boxes, ring: "border-upcoming/60", label: "Vendor" },
};

const SENSITIVITY_DOT: Record<number, string> = {
  5: "bg-critical",
  4: "bg-high",
  3: "bg-medium",
  2: "bg-low",
  1: "bg-pass",
};

export type GraphNodeData = {
  label: string;
  kind: string;
  personal_data?: boolean;
  sensitivity_level?: number;
  system?: string | null;
  country?: string | null;
  risk_level?: string | null;
};

function DataNodeComponent({ data }: { data: GraphNodeData }) {
  const meta = KIND_META[data.kind] || KIND_META.DATABASE;
  const Icon = meta.icon;
  const isVendor = data.kind === "VENDOR";
  return (
    <div
      className={cn(
        "min-w-[150px] rounded-lg border bg-panel px-3 py-2 shadow-md",
        meta.ring,
        isVendor && "rounded-full",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0 text-fg" />
        <div className="min-w-0">
          <div className="truncate text-xs font-semibold">{data.label}</div>
          <div className="text-[10px] text-muted">{meta.label}</div>
        </div>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5">
        {data.personal_data && (
          <span className="rounded bg-critical/15 px-1 py-0.5 text-[9px] font-medium text-critical">
            PII
          </span>
        )}
        {typeof data.sensitivity_level === "number" && data.sensitivity_level > 0 && (
          <span className="flex items-center gap-1 text-[9px] text-muted">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                SENSITIVITY_DOT[data.sensitivity_level] || "bg-muted",
              )}
            />
            S{data.sensitivity_level}
          </span>
        )}
        {data.country && (
          <span className="text-[9px] text-muted">{data.country}</span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  );
}

export const DataNode = memo(DataNodeComponent);
