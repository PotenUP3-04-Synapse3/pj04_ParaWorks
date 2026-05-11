export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const DEMO_USER_STORAGE_KEY = "paraworks-demo-user";
export const DEFAULT_DEMO_USER = "hanvv-employee";

export const LOCAL_DEMO_USERS = [
  {
    id: "demo-admin",
    email: "admin@paraworks.com",
    role: "admin",
    permission_levels: ["public", "internal", "restricted"],
    name: "ParaWorks Admin",
    title: "Workspace Administrator",
    department: "Platform",
  },
  {
    id: "google-hanvv-admin",
    email: "hanvv3@gmail.com",
    role: "admin",
    permission_levels: ["public", "internal", "restricted"],
    name: "Hanvv Admin",
    title: "Workspace Administrator",
    department: "Platform",
  },
  {
    id: "google-hanvv-employee",
    email: "hanvv3@koreacu.ac.kr",
    role: "employee",
    permission_levels: ["public", "internal"],
    name: "Hanvv Employee",
    title: "AI Agent Developer",
    department: "Engineering",
  },
  {
    id: "employee-mina",
    email: "mina@paraworks.com",
    role: "reviewer",
    permission_levels: ["public", "internal"],
    name: "Kim Mina",
    title: "Product Manager",
    department: "Product",
  },
  {
    id: "employee-jun",
    email: "jun@paraworks.com",
    role: "employee",
    permission_levels: ["public", "internal"],
    name: "Lee Jun",
    title: "Backend Engineer",
    department: "Engineering",
  },
  {
    id: "employee-soyeon",
    email: "soyeon@paraworks.com",
    role: "employee",
    permission_levels: ["public"],
    name: "Park Soyeon",
    title: "Operations Associate",
    department: "Operations",
  },
];

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

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift();
  return undefined;
}

function csrfHeader() {
  const token = getCookie("paraworks_csrf");
  return token ? { "X-CSRF-Token": token } : {};
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
      ...csrfHeader(),
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
      ...csrfHeader(),
    },
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  return parseResponse<T>(response);
}
