import { cn } from "@/lib/format";
import type { ReactNode } from "react";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
      {children}
    </thead>
  );
}

export function TH({
  children,
  className,
}: {
  children?: ReactNode;
  className?: string;
}) {
  return (
    <th className={cn("px-4 py-2 font-medium", className)}>{children}</th>
  );
}

export function TR({
  children,
  onClick,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-border/60",
        onClick && "cursor-pointer hover:bg-panel-2",
        className,
      )}
    >
      {children}
    </tr>
  );
}

export function TD({
  children,
  className,
}: {
  children?: ReactNode;
  className?: string;
}) {
  return <td className={cn("px-4 py-2.5 align-middle", className)}>{children}</td>;
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody>{children}</tbody>;
}

// Convenience for rendering a list into <tbody>. Keeps pages terse while
// letting each row control its own <tr> (key, onClick, cells).
export function TBodyRows<T>({
  rows,
  render,
}: {
  rows: T[];
  render: (row: T, index: number) => ReactNode;
}) {
  return <tbody>{rows.map((row, i) => render(row, i))}</tbody>;
}
