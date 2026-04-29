'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clearTokens } from '@/lib/api';
import { useRouter } from 'next/navigation';

const navItems = [
  { href: '/dashboard', label: '대시보드' },
  { href: '/projects', label: '프로젝트' },
  { href: '/review', label: '검토 큐' },
  { href: '/integrations', label: '연동' },
  { href: '/notifications', label: '알림' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    clearTokens();
    router.push('/login');
  };

  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-gray-100 flex flex-col py-6 px-4 gap-2">
      <div className="text-xl font-bold px-2 mb-6">ParaWorks</div>
      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              pathname.startsWith(item.href)
                ? 'bg-indigo-600 text-white'
                : 'hover:bg-gray-800 text-gray-300'
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <button
        onClick={handleLogout}
        className="px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 text-left"
      >
        로그아웃
      </button>
    </aside>
  );
}
