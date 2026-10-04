const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

let authToken = null;
let onUnauthorized = null;

export function setAuthToken(token) {
  authToken = token;
}

// Called by AuthProvider so a 401 (stale/expired/invalid token) bounces
// the user back to the login screen instead of every page silently failing.
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no body
  }

  if (!res.ok) {
    if (res.status === 401 && auth) {
      onUnauthorized?.();
    }
    const message = data?.detail || `Error ${res.status}`;
    throw new ApiError(message, res.status);
  }

  return data;
}

export const api = {
  auth: {
    status: () => request("/auth/status", { auth: false }),
    setup: (username, password) =>
      request("/auth/setup", { method: "POST", body: { username, password }, auth: false }),
    login: (username, password) =>
      request("/auth/login", { method: "POST", body: { username, password }, auth: false }),
    me: () => request("/auth/me"),
    changePassword: (current_password, new_password) =>
      request("/auth/change-password", { method: "POST", body: { current_password, new_password } }),
  },
  cameras: {
    list: () => request("/cameras"),
    sendNow: (id) => request(`/cameras/${id}/send-now`, { method: "POST" }),
    create: (payload) => request("/cameras", { method: "POST", body: payload }),
    update: (id, payload) => request(`/cameras/${id}`, { method: "PUT", body: payload }),
    remove: (id) => request(`/cameras/${id}`, { method: "DELETE" }),
    snapshot: async (id) => {
      let res;
      try {
        res = await fetch(`${API_BASE}/cameras/${id}/snapshot`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
          signal: AbortSignal.timeout(10000),
          cache: "no-store",
        });
      } catch {
        throw new ApiError("No se pudo conectar al servidor de vista previa. Reintentando...", 0);
      }
      if (!res.ok) {
        if (res.status === 401) onUnauthorized?.();
        const data = await res.json().catch(() => null);
        throw new ApiError(data?.detail || `Error del servidor de vista previa (${res.status})`, res.status);
      }
      return res.blob();
    },
  },
  apiConfig: {
    get: () => request("/api-config"),
    update: (payload) => request("/api-config", { method: "PUT", body: payload }),
  },
  stats: {
    summary: () => request("/stats/summary"),
    logs: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/stats/logs${q ? `?${q}` : ""}`);
    },
  },
};

export { ApiError };
