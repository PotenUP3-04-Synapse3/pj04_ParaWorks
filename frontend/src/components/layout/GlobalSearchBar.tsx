'use client';

import { Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useUIStore } from '@/lib/stores/uiStore';

export function GlobalSearchBar() {
  const router = useRouter();
  const { globalSearchQuery, setGlobalSearchQuery } = useUIStore();

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && globalSearchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(globalSearchQuery.trim())}`);
    }
  }

  return (
    <div className="relative w-72">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        type="text"
        value={globalSearchQuery}
        onChange={(e) => setGlobalSearchQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="전사 지식 검색 (Enter)"
        className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}
