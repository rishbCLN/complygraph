import { cn } from "@/lib/format";

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-critical/15 text-critical border-critical/30",
  HIGH: "bg-high/15 text-high border-high/30",
  MEDIUM: "bg-medium/15 text-medium border-medium/30",
  LOW: "bg-low/15 text-low border-low/30",
};

const STATUS_STYLES: Record<string, string> = {
  PASS: "bg-pass/15 text-pass border-pass/30",
  PARTIAL: "bg-medium/15 text-medium border-medium/30",
  FAIL: "bg-fail/15 text-fail border-fail/30",
  NO_EVIDENCE: "bg-high/15 text-high border-high/30",
  NEEDS_REVIEW: "bg-medium/15 text-medium border-medium/30",
  UPCOMING: "bg-upcoming/15 text-upcoming border-upcoming/30",
  NOT_APPLICABLE: "bg-muted/10 text-muted border-border",
  OPEN: "bg-high/15 text-high border-high/30",
  ACKNOWLEDGED: "bg-low/15 text-low border-low/30",
  IN_PROGRESS: "bg-low/15 text-low border-low/30",
  RESOLVED: "bg-pass/15 text-pass border-pass/30",
  ACCEPTED_RISK: "bg-upcoming/15 text-upcoming border-upcoming/30",
  FALSE_POSITIVE: "bg-muted/10 text-muted border-border",
  IN_FORCE: "bg-pass/15 text-pass border-pass/30",
  active: "bg-pass/15 text-pass border-pass/30",
  upcoming: "bg-upcoming/15 text-upcoming border-upcoming/30",
  FRESH: "bg-pass/15 text-pass border-pass/30",
  STALE: "bg-medium/15 text-medium border-medium/30",
  EXPIRED: "bg-fail/15 text-fail border-fail/30",
  UNKNOWN: "bg-muted/10 text-muted border-border",
  HIGH_RISK: "bg-high/15 text-high border-high/30",
  // AI-system architecture + lifecycle
  EXTERNAL: "bg-high/15 text-high border-high/30",
  CROSS_BORDER: "bg-high/15 text-high border-high/30",
  PRODUCTION: "bg-pass/15 text-pass border-pass/30",
  DEVELOPMENT: "bg-low/15 text-low border-low/30",
  TESTING: "bg-low/15 text-low border-low/30",
  PILOT: "bg-medium/15 text-medium border-medium/30",
  DEPRECATED: "bg-muted/10 text-muted border-border",
  RETIRED: "bg-muted/10 text-muted border-border",
  IDEA: "bg-muted/10 text-muted border-border",
  REVIEWED: "bg-pass/15 text-pass border-pass/30",
  NOT_REVIEWED: "bg-high/15 text-high border-high/30",
  IN_REVIEW: "bg-medium/15 text-medium border-medium/30",
  NEEDS_RE_REVIEW: "bg-medium/15 text-medium border-medium/30",
};

export function Badge({
  label,
  variant,
  className,
}: {
  label: string;
  variant?: string;
  className?: string;
}) {
  const key = variant ?? label;
  const style =
    SEVERITY_STYLES[key] || STATUS_STYLES[key] || "bg-muted/10 text-muted border-border";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium tracking-wide whitespace-nowrap",
        style,
        className,
      )}
    >
      {label.replace(/_/g, " ")}
    </span>
  );
}
