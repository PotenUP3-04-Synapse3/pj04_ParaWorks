'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { notificationsApi } from '@/lib/api/notifications';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Bell, Check } from 'lucide-react';
import Link from 'next/link';
import type { NotificationType } from '@/lib/types/api';
import { cn } from '@/lib/utils';

const typeIcon: Record<NotificationType, string> = {
  review_request: '📋',
  sync_complete: '✅',
  sync_error: '❌',
  hitl_approval: '🤖',
  handover_request: '🔄',
  system: '🔔',
};

export default function NotificationsPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const userId = user?.id ?? '';

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications', userId],
    queryFn: () => notificationsApi.list(userId),
    enabled: !!userId,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', userId] }),
  });

  const markAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', userId] }),
  });

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-gray-900">알림</h1>
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
              {unreadCount}개 미읽음
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllMutation.mutate()}
            disabled={markAllMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            <Check className="w-3.5 h-3.5" /> 전체 읽음
          </button>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}
      {!isLoading && !notifications?.length && (
        <div className="bg-white rounded-xl border border-gray-200 px-5 py-10 text-center">
          <Bell className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">알림이 없습니다.</p>
        </div>
      )}

      <div className="space-y-2">
        {notifications?.map((n) => (
          <div
            key={n.id}
            className={cn(
              'flex gap-4 bg-white rounded-xl border px-5 py-4 transition-colors',
              n.is_read ? 'border-gray-200' : 'border-blue-200 bg-blue-50',
            )}
          >
            <div className="text-2xl flex-shrink-0 mt-0.5">
              {typeIcon[n.type] ?? '🔔'}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn('text-sm font-medium', n.is_read ? 'text-gray-700' : 'text-gray-900')}>
                {n.title}
              </p>
              {n.body && <p className="text-sm text-gray-600 mt-0.5">{n.body}</p>}
              <div className="flex items-center gap-3 mt-1.5">
                <span className="text-xs text-gray-400">
                  {format(new Date(n.created_at), 'MM.dd HH:mm', { locale: ko })}
                </span>
                {n.link && (
                  <Link
                    href={n.link}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    이동하기
                  </Link>
                )}
              </div>
            </div>
            {!n.is_read && (
              <button
                onClick={() => markReadMutation.mutate(n.id)}
                className="flex-shrink-0 text-xs text-gray-400 hover:text-gray-600"
              >
                읽음
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
