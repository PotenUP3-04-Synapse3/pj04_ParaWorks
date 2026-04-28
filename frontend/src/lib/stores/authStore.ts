import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserRead } from '@/lib/types/api';

interface AuthState {
  token: string | null;
  user: UserRead | null;
  setAuth: (token: string, user: UserRead) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
    }),
    {
      name: 'auth-storage',
      // 보안 고려: 프로덕션에서는 httpOnly cookie + refresh token 권장
    },
  ),
);
