"use client";

import { API_URL } from "@/lib/api";
import { ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type PortalPurpose = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  lawful_basis: string;
  requires_consent: boolean;
  is_sensitive: boolean;
};

type PortalInfo = {
  organization: string;
  notice: { version: number; title: string; body: string; published_at: string | null } | null;
  purposes: PortalPurpose[];
  request_types: string[];
};

async function portalFetch<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`${API_URL}/api/v1${path}`, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json" },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const message = data?.error?.message || data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof message === "string" ? message : "Request failed");
  }
  return data as T;
}

function humanize(s: string): string {
  return s
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function PrivacyCenterPage() {
  const { slug } = useParams<{ slug: string }>();
  const [info, setInfo] = useState<PortalInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [identifier, setIdentifier] = useState("");
  const [flash, setFlash] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const [requestType, setRequestType] = useState("");
  const [requestNotes, setRequestNotes] = useState("");

  useEffect(() => {
    if (!slug) return;
    portalFetch<PortalInfo>(`/privacy/${slug}`)
      .then((data) => {
        setInfo(data);
        if (data.request_types.length) setRequestType(data.request_types[0]);
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Could not load the Privacy Center."));
  }, [slug]);

  function requireIdentifier(): boolean {
    if (!identifier.trim()) {
      setFlash({ kind: "err", text: "Enter the email the organisation holds for you first." });
      return false;
    }
    return true;
  }

  async function consent(purposeId: string, action: "grant" | "withdraw") {
    if (!requireIdentifier()) return;
    setBusy(true);
    setFlash(null);
    try {
      const res = await portalFetch<{ message: string }>(`/privacy/${slug}/consent`, {
        method: "POST",
        body: { principal_identifier: identifier.trim(), purpose_id: purposeId, action },
      });
      setFlash({ kind: "ok", text: res.message });
    } catch (e) {
      setFlash({ kind: "err", text: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      setBusy(false);
    }
  }

  async function submitRequest() {
    if (!requireIdentifier()) return;
    setBusy(true);
    setFlash(null);
    try {
      const res = await portalFetch<{ message: string; reference: string | null }>(
        `/privacy/${slug}/requests`,
        {
          method: "POST",
          body: {
            principal_identifier: identifier.trim(),
            request_type: requestType,
            notes: requestNotes || undefined,
          },
        },
      );
      setFlash({
        kind: "ok",
        text: `${res.message}${res.reference ? ` Reference: ${res.reference}` : ""}`,
      });
      setRequestNotes("");
    } catch (e) {
      setFlash({ kind: "err", text: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md rounded-lg border border-border bg-panel p-6 text-center">
          <h1 className="text-base font-semibold">Privacy Center unavailable</h1>
          <p className="mt-2 text-sm text-muted">{loadError}</p>
        </div>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-sm text-muted">Loading Privacy Center…</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6 flex items-center gap-2">
        <ShieldCheck className="h-6 w-6 text-accent" />
        <div>
          <div className="text-lg font-semibold">{info.organization}</div>
          <div className="text-xs text-muted">Privacy Center</div>
        </div>
      </div>

      {/* Identity */}
      <div className="mb-4 rounded-lg border border-border bg-panel p-5">
        <label className="mb-1 block text-xs font-medium text-muted">Your email</label>
        <input
          type="email"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder="[email protected]"
          className="w-full rounded border border-border bg-panel-2 px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <p className="mt-2 text-[11px] text-muted">
          Use the email address the organisation holds for you. Your choices below apply to this
          identifier. Identity is confirmed before any data request is fulfilled.
        </p>
      </div>

      {flash && (
        <div
          className={
            flash.kind === "ok"
              ? "mb-4 rounded border border-pass/40 bg-pass/10 px-3 py-2 text-sm text-pass"
              : "mb-4 rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail"
          }
        >
          {flash.text}
        </div>
      )}

      {/* Notice */}
      {info.notice && (
        <div className="mb-4 rounded-lg border border-border bg-panel p-5">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold">{info.notice.title}</h2>
            <span className="text-[11px] text-muted">v{info.notice.version}</span>
          </div>
          <p className="mt-2 whitespace-pre-line text-sm text-muted">{info.notice.body}</p>
        </div>
      )}

      {/* Purposes / consent */}
      <div className="mb-4 rounded-lg border border-border bg-panel p-5">
        <h2 className="text-sm font-semibold">Your consent choices</h2>
        <p className="mt-1 text-xs text-muted">
          Grant or withdraw consent per purpose. Withdrawal is as easy as granting.
        </p>
        <div className="mt-4 space-y-3">
          {info.purposes.map((p) => (
            <div
              key={p.id}
              className="flex items-start justify-between gap-4 rounded border border-border bg-panel-2 p-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{p.name}</span>
                  {p.is_sensitive && (
                    <span className="rounded border border-warn/40 bg-warn/10 px-1.5 py-0.5 text-[10px] text-warn">
                      Sensitive
                    </span>
                  )}
                </div>
                {p.description && <p className="mt-0.5 text-xs text-muted">{p.description}</p>}
                <div className="mt-1 text-[11px] text-muted">Lawful basis: {p.lawful_basis}</div>
              </div>
              {p.requires_consent ? (
                <div className="flex shrink-0 gap-2">
                  <button
                    onClick={() => consent(p.id, "grant")}
                    disabled={busy}
                    className="rounded border border-pass/40 bg-pass/10 px-2.5 py-1 text-xs text-pass hover:bg-pass/20 disabled:opacity-50"
                  >
                    Grant
                  </button>
                  <button
                    onClick={() => consent(p.id, "withdraw")}
                    disabled={busy}
                    className="rounded border border-fail/40 bg-fail/10 px-2.5 py-1 text-xs text-fail hover:bg-fail/20 disabled:opacity-50"
                  >
                    Withdraw
                  </button>
                </div>
              ) : (
                <span className="shrink-0 text-[11px] text-muted">Required for service</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* DSR */}
      <div className="rounded-lg border border-border bg-panel p-5">
        <h2 className="text-sm font-semibold">Exercise your rights</h2>
        <p className="mt-1 text-xs text-muted">
          Request access to, correction of, or erasure of your personal data, or raise a grievance.
        </p>
        <div className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs text-muted">Request type</label>
            <select
              value={requestType}
              onChange={(e) => setRequestType(e.target.value)}
              className="w-full rounded border border-border bg-panel-2 px-3 py-2 text-sm outline-none focus:border-accent"
            >
              {info.request_types.map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted">Details (optional)</label>
            <textarea
              value={requestNotes}
              onChange={(e) => setRequestNotes(e.target.value)}
              rows={3}
              className="w-full rounded border border-border bg-panel-2 px-3 py-2 text-sm outline-none focus:border-accent"
              placeholder="Anything that helps us locate your data."
            />
          </div>
          <button
            onClick={submitRequest}
            disabled={busy}
            className="rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Submitting…" : "Submit request"}
          </button>
        </div>
      </div>

      <p className="mt-6 text-center text-[11px] text-muted">
        This portal records your stated preferences. It does not itself constitute legal advice or a
        determination of your rights.
      </p>
    </div>
  );
}
