import type { Envelope } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  status: number;
  errors: unknown;

  constructor(status: number, message: string, errors?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function storeTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("selected_venue_id");
}

/** Try to exchange the refresh token for a new access token. */
async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const body = await res.json();
    const data = body?.data;
    if (data?.access_token && data?.refresh_token) {
      storeTokens(data.access_token, data.refresh_token);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  _isRetry = false,
): Promise<Envelope<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) {
    return { data: null as unknown as T, meta: null, errors: null };
  }

  let body: Record<string, unknown>;
  try {
    body = await res.json();
  } catch {
    throw new ApiError(res.status, "Invalid response from server");
  }

  // On 401, attempt a single token refresh then retry the original request
  if (res.status === 401 && !_isRetry) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, options, true);
    }
    // Refresh failed — clear tokens and redirect to login
    clearTokens();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    throw new ApiError(
      res.status,
      (body.detail as string) || (body.message as string) || "Request failed",
      body.errors
    );
  }

  return body as Envelope<T>;
}

// ─── Convenience methods ────────────────────────────────────────────────

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(path: string, data: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: <T = null>(path: string) =>
    request<T>(path, { method: "DELETE" }),
};

export { ApiError };
