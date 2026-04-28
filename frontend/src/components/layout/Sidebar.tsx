'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Search,
  GitBranch,
  ClipboardList,
  FolderOpen,
  CheckSquare,
  Bell,
  Plug,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/lib/stores/uiStore';

const navItems = [
  { label: '대시보드', href: '/dashboard', icon: LayoutDashboard },
  { label: '지식 검색', href: '/search', icon: Search },
  { label: '지식 맵', href: '/knowledge-map', icon: GitBranch },
  { label: '의사결정', href: '/decisions', icon: ClipboardList },
  { label: '프로젝트', href: '/projects', icon: FolderOpen },
  { label: '검토 대기', href: '/review', icon: CheckSquare },
  { label: '알림', href: '/notifications', icon: Bell },
  { label: '데이터 연동', href: '/integrations', icon: Plug },
  { label: '관리자', href: '/admin', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        'relative flex flex-col h-full bg-gray-900 text-white transition-all duration-200',
        sidebarOpen ? 'w-56' : 'w-14',
      )}
    >
      {/* 로고 */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-gray-700">
        <div className="w-7 h-7 rounded-md bg-blue-500 flex-shrink-0 flex items-center justify-center text-sm font-bold">
          P
        </div>
        {sidebarOpen && (
          <span className="font-semibold text-base truncate">ParaWorks</span>
        )}
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 overflow-y-auto py-2">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-gray-700',
                active && 'bg-gray-700 text-blue-400',
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 접기/펼치기 버튼 */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-6 w-6 h-6 rounded-full bg-gray-700 border border-gray-600 flex items-center justify-center hover:bg-gray-600 z-10"
        aria-label={sidebarOpen ? '사이드바 접기' : '사이드바 펼치기'}
      >
        {sidebarOpen ? (
          <ChevronLeft className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
      </button>
    </aside>
  );
}
