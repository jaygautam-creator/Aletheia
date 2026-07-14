// Account client: signup/login/logout/me, profile edits, API-key management, and
// request history. Every call sets `credentials: "include"` so the httpOnly session
// cookie travels cross-origin (the backend's CORS is already configured with
// allow_credentials=True) — the cookie itself is never readable from JS.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface AccountUser {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
}

export interface ApiKeyInfo {
  provider: string;
  masked_key: string;
  created_at: string;
  last_used_at: string | null;
}

export interface HistoryEntry {
  id: string;
  user_id: string | null;
  route: string;
  query_preview: string | null;
  key_source: string;
  provider: string;
  status: string;
  latency_ms: number | null;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Could not reach the backend — is it running?");
  }
  if (!response.ok) {
    let detail: string | undefined;
    try {
      detail = ((await response.json()) as { detail?: string }).detail;
    } catch {
      // Non-JSON error body: fall through to the status-based message.
    }
    throw new Error(detail ?? `Request failed (HTTP ${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function signup(email: string, password: string, displayName?: string): Promise<AccountUser> {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, display_name: displayName ?? null }),
  });
}

export function login(email: string, password: string): Promise<AccountUser> {
  return request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function logout(): Promise<{ ok: boolean }> {
  return request("/auth/logout", { method: "POST" });
}

export function me(): Promise<AccountUser> {
  return request("/auth/me");
}

export function updateProfile(input: { display_name?: string; email?: string }): Promise<AccountUser> {
  return request("/profile", { method: "PATCH", body: JSON.stringify(input) });
}

export function listApiKeys(): Promise<ApiKeyInfo[]> {
  return request("/profile/api-keys");
}

export function putApiKey(provider: string, key: string): Promise<ApiKeyInfo> {
  return request(`/profile/api-keys/${provider}`, { method: "PUT", body: JSON.stringify({ key }) });
}

export function deleteApiKey(provider: string): Promise<{ ok: boolean }> {
  return request(`/profile/api-keys/${provider}`, { method: "DELETE" });
}

export function myHistory(limit = 50, offset = 0): Promise<HistoryEntry[]> {
  return request(`/history/me?limit=${limit}&offset=${offset}`);
}

export function adminHistory(limit = 50, offset = 0): Promise<HistoryEntry[]> {
  return request(`/history/admin?limit=${limit}&offset=${offset}`);
}
