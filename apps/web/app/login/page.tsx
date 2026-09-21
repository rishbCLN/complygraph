"use client";

import { Button } from "@/components/button";
import { API_URL, apiFetch, ApiError, setActiveOrg } from "@/lib/api";
import { useSSOProviders } from "@/lib/queries";
import type { Me } from "@/lib/types";
import { KeyRound, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

const DEMO_USERS = [
  { email: "admin@asterlane.demo", role: "Admin" },
  { email: "privacy@asterlane.demo", role: "Privacy Officer" },
  { email: "security@asterlane.demo", role: "Security Analyst" },
  { email: "auditor@asterlane.demo", role: "Auditor" },
];

type MfaChallenge = { mfa_required: true; mfa_token: string };

function isMfaChallenge(v: Me | MfaChallenge): v is MfaChallenge {
  return (v as MfaChallenge).mfa_required === true;
}

export default function LoginPage() {
  const router = useRouter();
  const providers = useSSOProviders();
  const [email, setEmail] = useState("admin@asterlane.demo");
  const [password, setPassword] = useState("DemoPass123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // MFA challenge step
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  function finish(me: Me) {
    setActiveOrg(me.organization.id);
    router.push("/dashboard");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch<Me | MfaChallenge>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      if (isMfaChallenge(res)) {
        setMfaToken(res.mfa_token);
      } else {
        finish(res);
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Login failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function submitMfa(e: React.FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setLoading(true);
    try {
      const me = await apiFetch<Me>("/auth/mfa/login", {
        method: "POST",
        body: { mfa_token: mfaToken, code: mfaCode.trim() },
      });
      finish(me);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "That code is incorrect.",
      );
    } finally {
      setLoading(false);
    }
  }

  const ssoProviders = providers.data?.providers ?? [];

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-accent" />
          <span className="text-lg font-semibold">ComplyGraph</span>
        </div>
        <div className="rounded-lg border border-border bg-panel p-6">
          {mfaToken ? (
            <>
              <h1 className="text-base font-semibold">Two-factor authentication</h1>
              <p className="mt-1 text-xs text-muted">
                Enter the 6-digit code from your authenticator app, or a backup code.
              </p>
              <form onSubmit={submitMfa} className="mt-5 space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-muted">
                    Verification code
                  </label>
                  <input
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    className="w-full rounded border border-border bg-panel-2 px-3 py-2 font-mono text-sm outline-none focus:border-accent"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    autoFocus
                    placeholder="123456"
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
                  {loading ? "Verifying…" : "Verify"}
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    setMfaToken(null);
                    setMfaCode("");
                    setError(null);
                  }}
                  className="w-full text-center text-xs text-muted hover:text-fg"
                >
                  Back to sign in
                </button>
              </form>
            </>
          ) : (
            <>
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

              {ssoProviders.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted">
                    <span className="h-px flex-1 bg-border" />
                    or continue with
                    <span className="h-px flex-1 bg-border" />
                  </div>
                  <div className="space-y-2">
                    {ssoProviders.map((p) => (
                      <Button
                        key={p.protocol}
                        type="button"
                        variant="secondary"
                        className="w-full"
                        onClick={() => {
                          window.location.href = `${API_URL}${p.login_url}`;
                        }}
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                        {p.name}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {!mfaToken && (
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
        )}
      </div>
    </div>
  );
}
