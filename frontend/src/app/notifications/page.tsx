'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

interface Notification {
  id: string;
  notification_type: string;
  title: string;
  message: string | null;
  source_link: string | null;
  is_read: boolean;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const load = () =>
    apiFetch<Notification[]>('/notifications').then(setNotifications);

  useEffect(() => { load(); }, []);

  const markRead = async (id: string) => {
    await apiFetch(`/notifications/${id}/read`, { method: 'POST' });
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const markAll = async () => {
    await apiFetch('/notifications/read-all', { method: 'POST' });
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">알림 {unreadCount > 0 && <span className="text-sm text-indigo-600">({unreadCount})</span>}</h1>
        {unreadCount > 0 && (
          <button onClick={markAll} className="text-sm text-indigo-600 hover:underline">
            모두 읽음
          </button>
        )}
      </div>
      <div className="space-y-3">
        {notifications.map((n) => (
          <div
            key={n.id}
            className={`bg-white rounded-xl shadow px-5 py-4 flex justify-between items-start ${
              !n.is_read ? 'border-l-4 border-indigo-500' : ''
            }`}
          >
            <div>
              <p className="font-medium">{n.title}</p>
              {n.message && <p className="text-sm text-gray-500 mt-0.5">{n.message}</p>}
              {n.source_link && (
                <a href={n.source_link} className="text-xs text-indigo-500 hover:underline mt-1 block" target="_blank">
                  원본 보기
                </a>
              )}
            </div>
            {!n.is_read && (
              <button onClick={() => markRead(n.id)} className="text-xs text-gray-400 hover:underline ml-4 shrink-0">
                읽음
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
