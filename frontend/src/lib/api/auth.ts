import { apiFetch, apiPost } from './client';
import type { LoginRequest, LoginResponse, UserRead } from '@/lib/types/api';

export const authApi = {
  login: (body: LoginRequest) =>
    apiPost<LoginResponse>('auth/login', body),

  me: () => apiFetch<UserRead>('auth/me'),
};
