const ACCESS_KEY = "mai_access_token";
const REFRESH_KEY = "mai_refresh_token";

const AUTH_PATHS = new Set([
  "/api/auth/login",
  "/api/auth/refresh",
  "/api/auth/register",
]);

let refreshPromise = null;
let redirectingToLogin = false;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getAccessToken() {
  try {
    return localStorage.getItem(ACCESS_KEY) || null;
  } catch {
    return null;
  }
}

export function getRefreshToken() {
  try {
    return localStorage.getItem(REFRESH_KEY) || null;
  } catch {
    return null;
  }
}

export function setTokens({ access_token, refresh_token }) {
  try {
    if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
  } catch {
    /* storage unavailable — tokens stay in memory only for this page */
  }
}

export function clearTokens() {
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    /* storage unavailable */
  }
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

export function logout() {
  clearTokens();
}

function authHeaders() {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function redirectToLogin() {
  if (redirectingToLogin) return;
  const path = window.location.pathname || "/";
  if (path === "/login" || path === "/login/") return;
  redirectingToLogin = true;
  const next = encodeURIComponent(path + window.location.search);
  window.location.href = `/login?next=${next}`;
}

async function readError(res) {
  try {
    const body = await res.json();
    return body.detail || body.message || res.statusText;
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function refreshTokens() {
  if (refreshPromise) return refreshPromise;
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  refreshPromise = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      const data = await res.json();
      if (!data.access_token) {
        clearTokens();
        return false;
      }
      setTokens(data);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function request(path, options = {}) {
  const {
    method = "GET",
    body,
    headers = {},
    auth = true,
    redirectOnFail = true,
    _retried = false,
  } = options;

  const isAuthPath = AUTH_PATHS.has(path);
  const fetchHeaders = { ...headers };
  if (body !== undefined && fetchHeaders["Content-Type"] === undefined) {
    fetchHeaders["Content-Type"] = "application/json";
  }
  if (auth && !isAuthPath) {
    Object.assign(fetchHeaders, authHeaders());
  }

  let res;
  try {
    res = await fetch(path, {
      method,
      headers: fetchHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server", 0);
  }

  if (res.status === 401 && auth && !isAuthPath && !_retried) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return request(path, { ...options, _retried: true });
    }
    if (redirectOnFail) redirectToLogin();
    throw new ApiError("Session expired", 401);
  }

  if (!res.ok) {
    const message = await readError(res);
    if (res.status === 401 && auth && !isAuthPath && redirectOnFail) {
      redirectToLogin();
    }
    throw new ApiError(message, res.status);
  }

  if (res.status === 204) return null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  get: (path, options) => request(path, { ...options, method: "GET" }),
  post: (path, body, options) =>
    request(path, { ...options, method: "POST", body }),
  put: (path, body, options) =>
    request(path, { ...options, method: "PUT", body }),
  patch: (path, body, options) =>
    request(path, { ...options, method: "PATCH", body }),
  del: (path, options) => request(path, { ...options, method: "DELETE" }),
};

export async function login(username, password) {
  const data = await request("/api/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
    redirectOnFail: false,
  });
  setTokens(data);
  return data;
}

export async function register(username, password) {
  await request("/api/auth/register", {
    method: "POST",
    body: { username, password },
    auth: false,
    redirectOnFail: false,
  });
  return login(username, password);
}

export async function me(options) {
  return request("/api/auth/me", options);
}

window.MaiApi = { api, login, register, me, logout, request };
