'use client'

import { GlobalSearchBar } from './GlobalSearchBar'
import { NotificationBell } from './NotificationBell'
import { useAuthStore } from '@/lib/stores/authStore'
import { useUIStore } from '@/lib/stores/uiStore'

export function Header() {
  const user = useAuthStore((s) => s.user)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="rounded p-1.5 hover:bg-gray-100 transition-colors"
          aria-label="사이드바 토글"
        >
          <svg className="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="font-bold text-blue-600 text-lg hidden sm:block">ParaWorks</span>
      </div>

      <div className="flex items-center gap-3">
        <GlobalSearchBar />
        <NotificationBell />
        {user && (
          <div className="flex items-center gap-2">
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatar_url}
                alt={user.name}
                className="h-8 w-8 rounded-full object-cover"
              />
            ) : (
              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
                {user.name[0]?.toUpperCase()}
              </div>
            )}
            <span className="hidden sm:block text-sm text-gray-700 font-medium">{user.name}</span>
          </div>
        )}
      </div>
    </header>
  )
}
