"use client";

import { useSearch } from "@/lib/queries";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Badge } from "./badge";

export function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data, isFetching } = useSearch(q);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function go(path: string) {
    setOpen(false);
    setQ("");
    router.push(path);
  }

  const hasResults =
    data &&
    (data.assets.length ||
      data.findings.length ||
      data.controls.length ||
      data.vendors.length);

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 rounded border border-border bg-panel-2 px-2 py-1.5">
        <Search className="h-3.5 w-3.5 text-muted" />
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search assets, findings, controls…"
          className="w-64 bg-transparent text-xs outline-none placeholder:text-muted"
        />
      </div>
      {open && q.trim().length >= 2 && (
        <div className="absolute right-0 top-full z-50 mt-1 w-96 rounded-lg border border-border bg-panel shadow-xl">
          {isFetching && (
            <div className="px-3 py-3 text-xs text-muted">Searching…</div>
          )}
          {!isFetching && !hasResults && (
            <div className="px-3 py-3 text-xs text-muted">No matches.</div>
          )}
          {!isFetching && hasResults && (
            <div className="max-h-96 overflow-y-auto py-1">
              {data!.findings.length > 0 && (
                <Group title="Findings">
                  {data!.findings.map((f) => (
                    <Row key={f.id} onClick={() => go(`/findings/${f.id}`)}>
                      <span className="truncate">{f.label}</span>
                      <Badge label={f.severity} />
                    </Row>
                  ))}
                </Group>
              )}
              {data!.assets.length > 0 && (
                <Group title="Assets">
                  {data!.assets.map((a) => (
                    <Row key={a.id} onClick={() => go(`/data-assets/${a.id}`)}>
                      <span className="truncate">{a.label}</span>
                      <span className="text-muted">{a.type}</span>
                    </Row>
                  ))}
                </Group>
              )}
              {data!.controls.length > 0 && (
                <Group title="Controls">
                  {data!.controls.map((c) => (
                    <Row key={c.id} onClick={() => go(`/controls/${c.id}`)}>
                      <span className="truncate">{c.label}</span>
                    </Row>
                  ))}
                </Group>
              )}
              {data!.vendors.length > 0 && (
                <Group title="Vendors">
                  {data!.vendors.map((v) => (
                    <Row key={v.id} onClick={() => go(`/vendors/${v.id}`)}>
                      <span className="truncate">{v.label}</span>
                    </Row>
                  ))}
                </Group>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-1">
      <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted/70">
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-xs hover:bg-panel-2"
    >
      {children}
    </button>
  );
}
