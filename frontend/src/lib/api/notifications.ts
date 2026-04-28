import { apiFetch, apiPatch, apiPost } from './client';
import type { NotificationRead, UUID } from '@/lib/types/api';

export const notificationsApi = {
  list: (userId: UUID, unreadOnly = false) =>
    apiFetch<NotificationRead[]>('notifications', {
      searchParams: { user_id: userId, unread_only: String(unreadOnly) },
    }),

  markRead: (id: UUID) => apiPatch<NotificationRead>(`notifications/${id}/read`, {}),

  markAllRead: () => apiPost<void>('notifications/read-all', {}),
};
