/** Typed API client. Handles the backend's error envelope and one silent token refresh. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let accessToken: string | null = null;
export const tokenStore = {
  get: () => accessToken,
  set: (t: string | null) => {
    accessToken = t;
  },
};

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const e = body?.error;
    if (e?.code) return new ApiError(res.status, e.code, e.message ?? res.statusText, e.details);
  } catch {
    /* non-JSON body */
  }
  return new ApiError(res.status, "http_error", res.statusText || "Request failed");
}

async function raw(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}/api/v1${path}`, { ...init, headers, credentials: "include" });
}

/** Exchange the httpOnly refresh cookie for a new access token. */
export async function refreshSession(): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    tokenStore.set(null);
    return false;
  }
  tokenStore.set((await res.json()).access_token);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await raw(path, init);
  if (res.status === 401 && tokenStore.get() && !path.startsWith("/auth/")) {
    if (await refreshSession()) res = await raw(path, init);
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
