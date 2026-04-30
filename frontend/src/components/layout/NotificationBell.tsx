'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface Notification {
  id: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)

  const unread = notifications.filter((n) => !n.is_read).length

  useEffect(() => {
    api.get<{ items: Notification[] }>('/notifications?limit=10')
      .then((r) => setNotifications(r.items ?? []))
      .catch(() => {})
  }, [open])

  const markRead = async (id: string) => {
    await api.post(`/notifications/${id}/read`)
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-full p-1.5 hover:bg-gray-100 transition-colors"
        aria-label="알림"
      >
        <svg className="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-40 w-80 rounded-xl bg-white shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b">
              <span className="font-semibold text-sm text-gray-900">알림</span>
              <Link
                href="/notifications"
                className="text-xs text-blue-600 hover:underline"
                onClick={() => setOpen(false)}
              >
                전체 보기
              </Link>
            </div>
            <ul className="max-h-80 overflow-y-auto divide-y divide-gray-50">
              {notifications.length === 0 && (
                <li className="px-4 py-6 text-center text-sm text-gray-400">알림이 없습니다</li>
              )}
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={`px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${!n.is_read ? 'bg-blue-50/50' : ''}`}
                  onClick={() => markRead(n.id)}
                >
                  <p className="text-sm font-medium text-gray-800 line-clamp-1">{n.title}</p>
                  <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{n.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
