'use client';

import { Bell } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { notificationsApi } from '@/lib/api/notifications';
import { useAuthStore } from '@/lib/stores/authStore';

export function NotificationBell() {
  const user = useAuthStore((s) => s.user);

  const { data } = useQuery({
    queryKey: ['notifications-unread', user?.id],
    queryFn: () => notificationsApi.list(user!.id, true),
    enabled: !!user,
    refetchInterval: 30_000,
  });

  const count = data?.length ?? 0;

  return (
    <Link href="/notifications" className="relative p-1.5 hover:bg-gray-100 rounded-md">
      <Bell className="w-5 h-5 text-gray-600" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center px-1">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </Link>
  );
}
