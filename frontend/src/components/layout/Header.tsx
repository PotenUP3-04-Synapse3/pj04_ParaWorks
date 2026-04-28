'use client';

import { GlobalSearchBar } from './GlobalSearchBar';
import { NotificationBell } from './NotificationBell';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';

export function Header() {
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  function handleLogout() {
    clearAuth();
    router.push('/login');
  }

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 h-14">
      <GlobalSearchBar />

      <div className="flex items-center gap-3">
        <NotificationBell />

        {/* 사용자 아바타 */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium select-none">
            {user?.display_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="hidden md:block text-sm">
            <p className="font-medium text-gray-800 leading-none">{user?.display_name}</p>
            <p className="text-gray-500 text-xs capitalize">{user?.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs text-gray-400 hover:text-gray-700 ml-1"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>
  );
}
