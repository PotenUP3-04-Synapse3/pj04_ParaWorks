'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { clearTokens } from '@/lib/api'

export interface AuthUser {
  id: string
  email: string
  name: string
  role: string
  avatar_url: string | null
  organization_id: string
  department_id: string | null
  team_id: string | null
}

interface AuthStore {
  user: AuthUser | null
  setUser: (user: AuthUser | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      logout: () => {
        clearTokens()
        set({ user: null })
        window.location.href = '/login'
      },
    }),
    {
      name: 'paraworks-auth',
      partialize: (state) => ({ user: state.user }),
    },
  ),
)
