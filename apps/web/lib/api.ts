// Central API client. Talks to the FastAPI backend using cookie-based sessions.
// The session cookie is httpOnly and set by the backend on login; we send it
// with credentials: "include". The active organization id (returned by /auth/me)
// is echoed back via the x-organization-id header so tenant scoping is explicit.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const ORG_KEY = "complygraph.org_id";

export function setActiveOrg(orgId: string | null) {
  if (typeof window === "undefined") return;
  if (orgId) window.localStorage.setItem(ORG_KEY, orgId);
  else window.localStorage.removeItem(ORG_KEY);
}

export function getActiveOrg(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ORG_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  // when true, returns the raw Response (used for file downloads)
  raw?: boolean;
  headers?: Record<string, string>;
};

export async function apiFetch<T = unknown>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers || {}),
  };
  const org = getActiveOrg();
  if (org) headers["x-organization-id"] = org;

  const res = await fetch(`${API_URL}/api/v1${path}`, {
    method: opts.method || "GET",
    credentials: "include",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });

  if (opts.raw) {
    if (!res.ok) throw new ApiError(res.status, `Request failed (${res.status})`);
    return res as unknown as T;
  }

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail =
      (data as { detail?: unknown } | null)?.detail ?? `Request failed (${res.status})`;
    const message =
      typeof detail === "string" ? detail : `Request failed (${res.status})`;
    throw new ApiError(res.status, message, detail);
  }

  return data as T;
}

// Convenience for endpoints that live outside /api/v1 (health/ready).
export async function rootFetch<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    cache: "no-store",
  });
  return (await res.json()) as T;
}

export function downloadUrl(path: string): string {
  return `${API_URL}/api/v1${path}`;
}
