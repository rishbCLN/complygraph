import clsx from "clsx";

export function cn(...args: Parameters<typeof clsx>) {
  return clsx(...args);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

export function titleCase(s: string | null | undefined): string {
  if (!s) return "—";
  return s
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
export function sortSeverities<T extends { severity: string }>(rows: T[]): T[] {
  return [...rows].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
}
