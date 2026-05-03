export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const DEMO_USER_STORAGE_KEY = "paraworks-demo-user";
const DEFAULT_DEMO_USER = "hanvv-employee";

function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return typeof window === "undefined" ? `${API_BASE}${normalizedPath}` : normalizedPath;
}

export function getStoredDemoUserId() {
  if (typeof window === "undefined") {
    return DEFAULT_DEMO_USER;
  }

  return window.localStorage.getItem(DEMO_USER_STORAGE_KEY) || DEFAULT_DEMO_USER;
}

export function setStoredDemoUserId(userId: string) {
  window.localStorage.setItem(DEMO_USER_STORAGE_KEY, userId);
}

export function clearStoredDemoUserId() {
  window.localStorage.removeItem(DEMO_USER_STORAGE_KEY);
}

function demoUserHeader(demoUser?: string) {
  return demoUser ?? getStoredDemoUserId();
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string, demoUser?: string): Promise<T> {
  const response = await fetch(apiUrl(path), {
    headers: {
      "X-Demo-User": demoUserHeader(demoUser),
    },
    credentials: "include",
    cache: "no-store",
  });

  return parseResponse<T>(response);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  demoUser?: string,
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User": demoUserHeader(demoUser),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  return parseResponse<T>(response);
}

export async function apiPatch<T>(
  path: string,
  body: unknown,
  demoUser?: string,
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User": demoUserHeader(demoUser),
    },
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  return parseResponse<T>(response);
}
