import ky, { type KyInstance, type Options, HTTPError } from 'ky';
import type { ApiError } from '@/lib/types/api';

// authStore는 순환 참조 방지를 위해 동적으로 읽음
function getToken(): string | null {
  try {
    const raw = localStorage.getItem('auth-storage');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: { token?: string } };
    return parsed?.state?.token ?? null;
  } catch {
    return null;
  }
}

function redirectToLogin(): void {
  localStorage.removeItem('auth-storage');
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
}

const baseUrl =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// 베이스 ky 인스턴스 (훅 없음 — 훅 타입 호환성 문제 회피)
export const apiClient: KyInstance = ky.create({
  prefix: `${baseUrl}/api/v1`,
  timeout: 30_000,
});

/** 현재 토큰에서 Authorization 헤더 반환 */
function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 401 처리를 포함한 공통 에러 핸들러 */
function handle401(err: unknown): never {
  if (err instanceof HTTPError && err.response.status === 401) {
    redirectToLogin();
  }
  throw err;
}

/** API 에러를 표준 ApiError로 변환 */
export async function toApiError(err: unknown): Promise<ApiError> {
  if (err instanceof HTTPError) {
    try {
      const body = (await err.response.clone().json()) as { detail?: string };
      return { status: err.response.status, detail: body.detail ?? err.message };
    } catch {
      return { status: err.response.status, detail: err.message };
    }
  }
  return { status: 0, detail: String(err) };
}

/** 편의용 타입 안전 GET */
export async function apiFetch<T>(
  url: string,
  options?: Options,
): Promise<T> {
  return apiClient
    .get(url, { ...options, headers: { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) } })
    .json<T>()
    .catch(handle401);
}

/** 편의용 타입 안전 POST */
export async function apiPost<T>(
  url: string,
  json: unknown,
  options?: Options,
): Promise<T> {
  return apiClient
    .post(url, { json, ...options, headers: { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) } })
    .json<T>()
    .catch(handle401);
}

/** 편의용 타입 안전 PATCH */
export async function apiPatch<T>(
  url: string,
  json: unknown,
  options?: Options,
): Promise<T> {
  return apiClient
    .patch(url, { json, ...options, headers: { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) } })
    .json<T>()
    .catch(handle401);
}

/** 편의용 타입 안전 DELETE */
export async function apiDelete(url: string, options?: Options): Promise<void> {
  await apiClient
    .delete(url, { ...options, headers: { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) } })
    .catch(handle401);
}
