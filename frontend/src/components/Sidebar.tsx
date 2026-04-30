'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/authStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/dashboard', label: '대시보드', icon: '🏠' },
  { href: '/projects', label: '프로젝트', icon: '📁' },
  { href: '/decisions', label: '의사결정', icon: '⚖️' },
  { href: '/search', label: '검색', icon: '🔍' },
  { href: '/knowledge-map', label: '지식 맵', icon: '🗺️' },
  { href: '/review', label: '검토 큐', icon: '✅' },
  { href: '/integrations', label: '연동', icon: '🔗' },
  { href: '/notifications', label: '알림', icon: '🔔' },
];

const adminItems = [
  { href: '/admin', label: '관리자', icon: '⚙️' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuthStore();
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const isAdmin = user?.role === 'admin';

  if (!sidebarOpen) {
    return (
      <aside className="w-14 min-h-screen bg-gray-900 text-gray-100 flex flex-col py-4 items-center gap-2">
        <div className="text-xl font-bold mb-4">P</div>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            title={item.label}
            className={cn(
              'w-9 h-9 flex items-center justify-center rounded-lg text-lg transition-colors',
              pathname.startsWith(item.href) ? 'bg-indigo-600' : 'hover:bg-gray-800',
            )}
          >
            {item.icon}
          </Link>
        ))}
      </aside>
    );
  }

  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-gray-100 flex flex-col py-6 px-4 gap-2 shrink-0">
      <div className="text-xl font-bold px-2 mb-6 text-blue-400">ParaWorks</div>
      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              pathname.startsWith(item.href)
                ? 'bg-indigo-600 text-white'
                : 'hover:bg-gray-800 text-gray-300',
            )}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
        {isAdmin && (
          <>
            <div className="mt-4 mb-1 px-3 text-xs text-gray-500 uppercase tracking-wider">관리</div>
            {adminItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  pathname.startsWith(item.href)
                    ? 'bg-indigo-600 text-white'
                    : 'hover:bg-gray-800 text-gray-300',
                )}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </>
        )}
      </nav>
      <button
        onClick={logout}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 text-left"
      >
        <span>🚪</span>
        로그아웃
      </button>
    </aside>
  );
}
