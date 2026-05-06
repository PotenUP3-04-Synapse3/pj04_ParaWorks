import { cookies } from "next/headers";
import { API_BASE, DEFAULT_DEMO_USER } from "./client";

function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalizedPath}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function serverApiGet<T>(path: string, demoUser = DEFAULT_DEMO_USER): Promise<T> {
  const requestCookies = await cookies();
  const cookieHeader = requestCookies.toString();
  const headers: Record<string, string> = {
    "X-Demo-User": demoUser,
  };

  if (cookieHeader) {
    headers.Cookie = cookieHeader;
  }

  const response = await fetch(apiUrl(path), {
    headers,
    cache: "no-store",
  });

  return parseResponse<T>(response);
}
