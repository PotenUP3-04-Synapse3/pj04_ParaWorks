const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path), {
    headers: {
      "X-Demo-User": "admin",
    },
    cache: "no-store",
  });

  return parseResponse<T>(response);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  demoUser = "admin",
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User": demoUser,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  return parseResponse<T>(response);
}
