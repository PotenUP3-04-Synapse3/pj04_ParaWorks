import { apiFetch, apiPatch } from './client';
import type { UserRead, AuditLogRead, UUID } from '@/lib/types/api';

export interface RoleUpdateBody {
  role: string;
  department_id?: UUID;
  team_id?: UUID;
}

export const adminApi = {
  listUsers: (orgId: UUID) =>
    apiFetch<UserRead[]>('admin/users', {
      searchParams: { org_id: orgId },
    }),

  updateUser: (id: UUID, body: RoleUpdateBody) =>
    apiPatch<UserRead>(`admin/users/${id}`, body),

  listAuditLogs: (orgId: UUID, params?: { skip?: number; limit?: number }) =>
    apiFetch<AuditLogRead[]>('admin/audit-logs', {
      searchParams: { org_id: orgId, ...params },
    }),
};
