"use client";

import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { EmptyState, ErrorState, Panel, Spinner } from "@/components/panel";
import { Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  useMfaActivate,
  useMfaDisable,
  useMfaEnroll,
  useMfaRegenerateBackupCodes,
  useMfaStatus,
} from "@/lib/queries";
import type { MfaEnrollment } from "@/lib/types";
import { Copy, ShieldCheck } from "lucide-react";
import { useState } from "react";

export default function SettingsSecurityPage() {
  const status = useMfaStatus();

  return (
    <div className="space-y-4">
      <Panel title="Two-factor authentication (TOTP)">
        {status.isLoading ? (
          <Spinner />
        ) : status.isError ? (
          <ErrorState message="Could not load MFA status." />
        ) : !status.data?.available ? (
          <EmptyState message="MFA is not enabled for this deployment. Set MFA_ENABLED to allow enrolment." />
        ) : status.data.enabled ? (
          <MfaEnabledView issuer={status.data.issuer} />
        ) : (
          <MfaEnrollView />
        )}
      </Panel>
    </div>
  );
}

function BackupCodes({ codes }: { codes: string[] }) {
  return (
    <div className="rounded border border-medium/40 bg-medium/10 p-3">
      <p className="mb-2 text-xs text-medium">
        Store these one-time backup codes somewhere safe. Each can be used once if
        you lose access to your authenticator. They are shown only once.
      </p>
      <div className="grid grid-cols-2 gap-1.5">
        {codes.map((c) => (
          <code
            key={c}
            className="rounded bg-panel px-2 py-1 text-center font-mono text-sm"
          >
            {c}
          </code>
        ))}
      </div>
    </div>
  );
}

function MfaEnrollView() {
  const enroll = useMfaEnroll();
  const activate = useMfaActivate();
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);

  function startEnroll() {
    setError(null);
    enroll.mutate(undefined, {
      onSuccess: (data) => setEnrollment(data),
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : "Could not start enrolment."),
    });
  }

  function submitActivate() {
    setError(null);
    if (!code.trim()) {
      setError("Enter the 6-digit code from your authenticator.");
      return;
    }
    activate.mutate(code.trim(), {
      onSuccess: (data) => setBackupCodes(data.backup_codes),
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : "That code is incorrect."),
    });
  }

  if (backupCodes) {
    return (
      <div className="space-y-4 p-4">
        <div className="flex items-center gap-2 text-sm text-pass">
          <ShieldCheck className="h-4 w-4" />
          Two-factor authentication is now active.
        </div>
        <BackupCodes codes={backupCodes} />
      </div>
    );
  }

  if (!enrollment) {
    return (
      <div className="space-y-3 p-4">
        <p className="text-sm text-muted">
          Add a second factor with any TOTP authenticator app (Google
          Authenticator, 1Password, Authy). You will scan a secret and confirm one
          code to activate.
        </p>
        {error && (
          <div className="rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail">
            {error}
          </div>
        )}
        <Button variant="primary" onClick={startEnroll} disabled={enroll.isPending}>
          {enroll.isPending ? "Starting…" : "Begin enrolment"}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="mb-1 text-sm">
          Enter this secret manually in your authenticator, or use the otpauth URI:
        </p>
        <div className="flex items-center gap-2 rounded border border-border bg-panel-2 px-3 py-2">
          <code className="flex-1 break-all font-mono text-sm">
            {enrollment.secret}
          </code>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigator.clipboard?.writeText(enrollment.secret)}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="mt-2 break-all font-mono text-xs text-muted">
          {enrollment.otpauth_uri}
        </p>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted">
          Verification code
        </label>
        <div className="flex items-center gap-2">
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="123456"
            inputMode="numeric"
            autoComplete="one-time-code"
            className="w-32 font-mono"
          />
          <Button
            variant="primary"
            onClick={submitActivate}
            disabled={activate.isPending}
          >
            {activate.isPending ? "Verifying…" : "Activate"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail">
          {error}
        </div>
      )}
    </div>
  );
}

function MfaEnabledView({ issuer }: { issuer: string }) {
  const regenerate = useMfaRegenerateBackupCodes();
  const disable = useMfaDisable();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [confirmDisable, setConfirmDisable] = useState(false);

  function regen() {
    setError(null);
    regenerate.mutate(undefined, {
      onSuccess: (data) => setBackupCodes(data.backup_codes),
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : "Could not regenerate codes."),
    });
  }

  function submitDisable() {
    setError(null);
    if (!password) {
      setError("Enter your password to disable MFA.");
      return;
    }
    disable.mutate(password, {
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : "Could not disable MFA."),
    });
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-2 text-sm">
        <Badge label="Enabled" variant="PASS" />
        <span className="text-muted">Protected by {issuer} (TOTP).</span>
      </div>

      {backupCodes && <BackupCodes codes={backupCodes} />}

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={regen} disabled={regenerate.isPending}>
          {regenerate.isPending ? "Regenerating…" : "Regenerate backup codes"}
        </Button>
        {!confirmDisable && (
          <Button variant="danger" onClick={() => setConfirmDisable(true)}>
            Disable MFA
          </Button>
        )}
      </div>

      {confirmDisable && (
        <div className="space-y-2 rounded border border-fail/40 bg-fail/10 p-3">
          <p className="text-sm text-fail">
            Confirm your password to disable two-factor authentication.
          </p>
          <div className="flex items-center gap-2">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Current password"
              autoComplete="current-password"
              className="w-56"
            />
            <Button
              variant="danger"
              onClick={submitDisable}
              disabled={disable.isPending}
            >
              {disable.isPending ? "Disabling…" : "Confirm disable"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmDisable(false);
                setPassword("");
                setError(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-fail">
          {error}
        </div>
      )}
    </div>
  );
}
