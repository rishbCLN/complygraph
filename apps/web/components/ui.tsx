"use client";

import { cn } from "@/lib/format";
import Link from "next/link";
import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-1 flex items-center gap-1.5 text-xs text-muted">
          {breadcrumbs.map((b, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {b.href ? (
                <Link href={b.href} className="hover:text-fg">
                  {b.label}
                </Link>
              ) : (
                <span className="text-fg">{b.label}</span>
              )}
              {i < breadcrumbs.length - 1 && <span>/</span>}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          {description && (
            <p className="mt-0.5 text-sm text-muted">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: string; label: string; count?: number }[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 border-b border-border">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
            active === t.key
              ? "border-accent text-fg"
              : "border-transparent text-muted hover:text-fg",
          )}
        >
          {t.label}
          {typeof t.count === "number" && (
            <span className="ml-1.5 rounded bg-panel-2 px-1.5 py-0.5 text-[10px] tabular-nums text-muted">
              {t.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export function Field({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
        {label}
      </div>
      <div className="mt-0.5 text-sm">{value ?? "—"}</div>
    </div>
  );
}

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "rounded border border-border bg-panel-2 px-2.5 py-1.5 text-sm outline-none focus:border-accent placeholder:text-muted",
        className,
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "rounded border border-border bg-panel-2 px-2.5 py-1.5 text-sm outline-none focus:border-accent",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  width?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden
      />
      <div
        className={cn(
          "relative flex h-full w-full flex-col border-l border-border bg-panel",
          width,
        )}
      >
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted hover:bg-panel-2 hover:text-fg"
          >
            ✕
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  danger,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} aria-hidden />
      <div className="relative w-full max-w-sm rounded-lg border border-border bg-panel p-5">
        <h2 className="text-sm font-semibold">{title}</h2>
        <div className="mt-2 text-sm text-muted">{message}</div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded border border-border bg-panel-2 px-3 py-1.5 text-sm hover:bg-border"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              "rounded border border-transparent px-3 py-1.5 text-sm text-white",
              danger ? "bg-fail/90 hover:bg-fail" : "bg-accent-2 hover:bg-accent",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded bg-panel-2", className)} />
  );
}

export function ScoreBar({ label, value, max = 5 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const tone =
    pct >= 80 ? "bg-critical" : pct >= 60 ? "bg-high" : pct >= 35 ? "bg-medium" : "bg-low";
  return (
    <div className="flex items-center gap-3">
      <div className="w-24 shrink-0 text-xs text-muted">{label}</div>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-panel-2">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-10 shrink-0 text-right text-xs tabular-nums">
        {value}/{max}
      </div>
    </div>
  );
}
