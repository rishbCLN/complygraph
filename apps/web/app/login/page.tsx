"use client";

import { Button } from "@/components/button";
import { apiFetch, ApiError, setActiveOrg } from "@/lib/api";
import type { Me } from "@/lib/types";
import { ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

const DEMO_USERS = [
  { email: "admin@asterlane.demo", role: "Admin" },
  { email: "privacy@asterlane.demo", role: "Privacy Officer" },
  { email: "security@asterlane.demo", role: "Security Analyst" },
  { email: "auditor@asterlane.demo", role: "Auditor" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@asterlane.demo");
  const [password, setPassword] = useState("DemoPass123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const me = await apiFetch<Me>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      setActiveOrg(me.organization.id);
      router.push("/dashboard");
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Login failed. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-accent" />
          <span className="text-lg font-semibold">ComplyGraph</span>
        </div>
        <div className="rounded-lg border border-border bg-panel p-6">
          <h1 className="text-base font-semibold">Sign in</h1>
          <p className="mt-1 text-xs text-muted">
            Continuous data governance for the DPDP Act 2023.
          </p>
          <form onSubmit={submit} className="mt-5 space-y-3">
            <div>
              <label className="mb-1 block text-xs text-muted">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded border border-border bg-panel-2 px-3 py-2 text-sm outline-none focus:border-accent"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded border border-border bg-panel-2 px-3 py-2 text-sm outline-none focus:border-accent"
                autoComplete="current-password"
              />
            </div>
            {error && (
              <div className="rounded border border-fail/40 bg-fail/10 px-3 py-2 text-xs text-fail">
                {error}
              </div>
            )}
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={loading}
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>

        <div className="mt-4 rounded-lg border border-border bg-panel-2 p-4">
          <div className="text-xs font-medium text-muted">
            Demo accounts (password: DemoPass123!)
          </div>
          <div className="mt-2 space-y-1">
            {DEMO_USERS.map((u) => (
              <button
                key={u.email}
                onClick={() => {
                  setEmail(u.email);
                  setPassword("DemoPass123!");
                }}
                className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs hover:bg-panel"
              >
                <span className="font-mono">{u.email}</span>
                <span className="text-muted">{u.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
