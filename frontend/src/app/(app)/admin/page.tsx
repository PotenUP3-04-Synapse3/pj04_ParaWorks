'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { adminApi } from '@/lib/api/admin';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { UserRole } from '@/lib/types/api';
import { useRouter } from 'next/navigation';

const roles: UserRole[] = ['admin', 'manager', 'member', 'viewer'];
const roleLabel: Record<UserRole, string> = {
  admin: '관리자',
  manager: '매니저',
  member: '멤버',
  viewer: '뷰어',
};

type Tab = 'users' | 'audit';

export default function AdminPage() {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const qc = useQueryClient();
  const orgId = user?.organization_id ?? '';
  const [tab, setTab] = useState<Tab>('users');

  // admin 권한 가드
  if (user && user.role !== 'admin') {
    router.replace('/dashboard');
    return null;
  }

  return (
    <div className="max-w-5xl space-y-5">
      <h1 className="text-2xl font-semibold text-gray-900">관리자</h1>

      {/* 탭 */}
      <div className="flex gap-1 border-b border-gray-200">
        {(['users', 'audit'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'users' ? '사용자 관리' : '감사 로그'}
          </button>
        ))}
      </div>

      {tab === 'users' && <UsersTab orgId={orgId} qc={qc} />}
      {tab === 'audit' && <AuditTab orgId={orgId} />}
    </div>
  );
}

function UsersTab({ orgId, qc }: { orgId: string; qc: ReturnType<typeof useQueryClient> }) {
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users', orgId],
    queryFn: () => adminApi.listUsers(orgId),
    enabled: !!orgId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      adminApi.updateUser(id, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users', orgId] }),
  });

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="px-4 py-3 text-left font-medium text-gray-600">이름</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">이메일</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">역할</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">상태</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">가입일</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {isLoading && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                불러오는 중...
              </td>
            </tr>
          )}
          {users?.map((u) => (
            <tr key={u.id}>
              <td className="px-4 py-3 font-medium text-gray-800">{u.display_name}</td>
              <td className="px-4 py-3 text-gray-600">{u.email}</td>
              <td className="px-4 py-3">
                <select
                  defaultValue={u.role}
                  onChange={(e) => updateMutation.mutate({ id: u.id, role: e.target.value })}
                  className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {roles.map((r) => (
                    <option key={r} value={r}>{roleLabel[r]}</option>
                  ))}
                </select>
              </td>
              <td className="px-4 py-3">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    u.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {u.is_active ? '활성' : '비활성'}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500">
                {format(new Date(u.created_at), 'yyyy.MM.dd', { locale: ko })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditTab({ orgId }: { orgId: string }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', orgId],
    queryFn: () => adminApi.listAuditLogs(orgId, { limit: 50 }),
    enabled: !!orgId,
  });

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="px-4 py-3 text-left font-medium text-gray-600">액션</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">행위자</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">대상</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">IP</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">일시</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {isLoading && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                불러오는 중...
              </td>
            </tr>
          )}
          {logs?.map((log) => (
            <tr key={log.id}>
              <td className="px-4 py-3 font-mono text-xs text-gray-700">{log.action}</td>
              <td className="px-4 py-3 text-gray-600">{log.actor_email ?? '—'}</td>
              <td className="px-4 py-3 text-gray-500">
                {log.resource_type && (
                  <span>
                    {log.resource_type}
                    {log.resource_id && (
                      <span className="ml-1 text-gray-400 text-xs">#{log.resource_id.slice(0, 8)}</span>
                    )}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-gray-400">{log.ip_address ?? '—'}</td>
              <td className="px-4 py-3 text-gray-500">
                {format(new Date(log.created_at), 'MM.dd HH:mm', { locale: ko })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
