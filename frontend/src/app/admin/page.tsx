'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table'
import { useAuthStore } from '@/lib/stores/authStore'
import { useRouter } from 'next/navigation'

interface AdminUser {
  id: string
  email: string
  name?: string
  role: string
  is_active: boolean
  department_id?: string
  team_id?: string
  created_at?: string
}

interface AuditLog {
  id: string
  user_email?: string
  action: string
  resource_type?: string
  resource_id?: string
  created_at: string
}

const ROLES = ['viewer', 'member', 'manager', 'admin']

const TABS = [
  { id: 'users', label: '사용자 관리' },
  { id: 'audit', label: '감사 로그' },
]

const colHelper = createColumnHelper<AdminUser>()

export default function AdminPage() {
  const user = useAuthStore((s) => s.user)
  const router = useRouter()
  const qc = useQueryClient()
  const [tab, setTab] = useState<'users' | 'audit'>('users')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editRole, setEditRole] = useState('')

  // Redirect non-admins
  if (user && user.role !== 'admin') {
    router.replace('/dashboard')
    return null
  }

  const { data: users, isLoading: usersLoading } = useQuery<AdminUser[]>({
    queryKey: ['admin-users'],
    queryFn: () => api.get<AdminUser[]>('/admin/users'),
    enabled: tab === 'users',
  })

  const { data: auditLogs, isLoading: auditLoading } = useQuery<AuditLog[]>({
    queryKey: ['admin-audit'],
    queryFn: () => api.get<AuditLog[]>('/admin/audit-logs'),
    enabled: tab === 'audit',
  })

  const patchUser = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<AdminUser> }) =>
      api.patch(`/admin/users/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setEditingId(null)
    },
  })

  const columns = [
    colHelper.accessor('email', {
      header: '이메일',
      cell: (info) => <span className="text-sm font-medium text-gray-900">{info.getValue()}</span>,
    }),
    colHelper.accessor('name', {
      header: '이름',
      cell: (info) => <span className="text-sm text-gray-700">{info.getValue() ?? '-'}</span>,
    }),
    colHelper.accessor('role', {
      header: '역할',
      cell: (info) => {
        const row = info.row.original
        if (editingId === row.id) {
          return (
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-xs"
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          )
        }
        return (
          <span className="rounded-full px-2 py-0.5 text-xs bg-blue-100 text-blue-700">
            {info.getValue()}
          </span>
        )
      },
    }),
    colHelper.accessor('is_active', {
      header: '활성',
      cell: (info) => (
        <span className={`text-xs font-medium ${info.getValue() ? 'text-green-600' : 'text-red-500'}`}>
          {info.getValue() ? '활성' : '비활성'}
        </span>
      ),
    }),
    colHelper.display({
      id: 'actions',
      header: '작업',
      cell: (info) => {
        const row = info.row.original
        if (editingId === row.id) {
          return (
            <div className="flex gap-2">
              <button
                onClick={() => patchUser.mutate({ id: row.id, payload: { role: editRole } })}
                disabled={patchUser.isPending}
                className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
              >
                저장
              </button>
              <button
                onClick={() => setEditingId(null)}
                className="rounded bg-gray-200 px-2 py-1 text-xs text-gray-700"
              >
                취소
              </button>
            </div>
          )
        }
        return (
          <div className="flex gap-2">
            <button
              onClick={() => { setEditingId(row.id); setEditRole(row.role) }}
              className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50"
            >
              수정
            </button>
            <button
              onClick={() => patchUser.mutate({ id: row.id, payload: { is_active: !row.is_active } })}
              className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50"
            >
              {row.is_active ? '비활성화' : '활성화'}
            </button>
          </div>
        )
      },
    }),
  ]

  const table = useReactTable({
    data: users ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">관리자 패널</h1>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as 'users' | 'audit')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Users tab */}
      {tab === 'users' && (
        <>
          {usersLoading ? (
            <div className="text-center py-12 text-gray-400">로딩 중...</div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="w-full">
                <thead className="bg-gray-50">
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((h) => (
                        <th
                          key={h.id}
                          className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                        >
                          {flexRender(h.column.columnDef.header, h.getContext())}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {(users?.length ?? 0) === 0 && (
                <div className="text-center py-10 text-gray-400 text-sm">사용자가 없습니다</div>
              )}
            </div>
          )}
        </>
      )}

      {/* Audit log tab */}
      {tab === 'audit' && (
        <>
          {auditLoading ? (
            <div className="text-center py-12 text-gray-400">로딩 중...</div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {['시간', '사용자', '액션', '리소스', 'ID'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {auditLogs?.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString('ko-KR')}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{log.user_email ?? '-'}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{log.action}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{log.resource_type ?? '-'}</td>
                      <td className="px-4 py-3 text-xs text-gray-400 font-mono truncate max-w-[120px]">
                        {log.resource_id ?? '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(auditLogs?.length ?? 0) === 0 && (
                <div className="text-center py-10 text-gray-400 text-sm">감사 로그가 없습니다</div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
