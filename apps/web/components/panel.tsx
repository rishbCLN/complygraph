import { cn } from "@/lib/format";
import type { ReactNode } from "react";

export function Panel({
  children,
  className,
  title,
  actions,
}: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-panel",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          {typeof title === "string" ? (
            <h2 className="text-sm font-semibold text-fg">{title}</h2>
          ) : (
            title
          )}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "critical" | "warn" | "good";
}) {
  const toneClass =
    tone === "critical"
      ? "text-critical"
      : tone === "warn"
        ? "text-medium"
        : tone === "good"
          ? "text-pass"
          : "text-fg";
  return (
    <div className="rounded-lg border border-border bg-panel px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={cn("mt-1 text-2xl font-semibold tabular-nums", toneClass)}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center px-4 py-12 text-sm text-muted">
      {message}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 px-4 py-12 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" />
      {label || "Loading…"}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="m-4 rounded border border-fail/40 bg-fail/10 px-4 py-3 text-sm text-fail">
      {message}
    </div>
  );
}
