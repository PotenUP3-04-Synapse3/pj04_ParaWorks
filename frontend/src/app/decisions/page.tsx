'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { ConfidenceBar } from '@/components/shared/ConfidenceBar'
import { PermissionBadge } from '@/components/shared/PermissionBadge'
import { useAuthStore } from '@/lib/stores/authStore'

interface Decision {
  id: string
  title: string
  decision_summary?: string
  business_domain?: string
  decided_at?: string
  confidence_score?: number
  review_status: string
  permission_level: string
}

const STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  draft: { label: '초안', cls: 'bg-gray-100 text-gray-600' },
  pending_review: { label: '검토 중', cls: 'bg-yellow-100 text-yellow-700' },
  approved: { label: '승인', cls: 'bg-green-100 text-green-700' },
  rejected: { label: '반려', cls: 'bg-red-100 text-red-700' },
  needs_more_evidence: { label: '증거 부족', cls: 'bg-orange-100 text-orange-700' },
  archived: { label: '보관', cls: 'bg-gray-100 text-gray-500' },
}

const DOMAIN_LABELS: Record<string, string> = {
  product: '프로덕트',
  engineering: '엔지니어링',
  marketing: '마케팅',
  sales: '영업',
  hr: 'HR',
  finance: '재무',
  operations: '운영',
  legal: '법무',
  other: '기타',
}

export default function DecisionsPage() {
  const user = useAuthStore((s) => s.user)
  const [statusFilter, setStatusFilter] = useState('')
  const [domainFilter, setDomainFilter] = useState('')
  const qc = useQueryClient()

  const { data: decisions, isLoading } = useQuery<Decision[]>({
    queryKey: ['decisions', statusFilter, domainFilter],
    queryFn: () => {
      const params = new URLSearchParams()
      if (statusFilter) params.set('review_status', statusFilter)
      if (domainFilter) params.set('business_domain', domainFilter)
      return api.get<Decision[]>(`/decisions?${params}`)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/decisions/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['decisions'] }),
  })

  const isManager = user?.role === 'admin' || user?.role === 'manager'

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">의사결정 기록</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm bg-white"
        >
          <option value="">모든 상태</option>
          {Object.entries(STATUS_LABELS).map(([v, { label }]) => (
            <option key={v} value={v}>{label}</option>
          ))}
        </select>
        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm bg-white"
        >
          <option value="">모든 도메인</option>
          {Object.entries(DOMAIN_LABELS).map(([v, label]) => (
            <option key={v} value={v}>{label}</option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="text-center py-12 text-gray-400">로딩 중...</div>
      )}

      <div className="space-y-3">
        {decisions?.map((d) => {
          const statusCfg = STATUS_LABELS[d.review_status] ?? { label: d.review_status, cls: 'bg-gray-100' }
          return (
            <div key={d.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.cls}`}>
                      {statusCfg.label}
                    </span>
                    {d.business_domain && (
                      <span className="rounded-full px-2 py-0.5 text-xs bg-purple-100 text-purple-700">
                        {DOMAIN_LABELS[d.business_domain] ?? d.business_domain}
                      </span>
                    )}
                    <PermissionBadge level={d.permission_level} />
                  </div>
                  <Link
                    href={`/decisions/${d.id}`}
                    className="font-semibold text-gray-900 hover:text-blue-600 transition-colors block truncate"
                  >
                    {d.title}
                  </Link>
                  {d.decision_summary && (
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{d.decision_summary}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2">
                    {typeof d.confidence_score === 'number' && (
                      <ConfidenceBar score={d.confidence_score} />
                    )}
                    {d.decided_at && (
                      <span className="text-xs text-gray-400">
                        {new Date(d.decided_at).toLocaleDateString('ko-KR')}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <Link
                    href={`/decisions/${d.id}`}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium hover:bg-gray-50 transition-colors"
                  >
                    상세 보기
                  </Link>
                  {isManager && d.review_status === 'pending_review' && (
                    <button
                      onClick={() => approveMutation.mutate(d.id)}
                      disabled={approveMutation.isPending}
                      className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-60"
                    >
                      승인
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {decisions?.length === 0 && !isLoading && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">의사결정 기록이 없습니다</p>
          <p className="text-sm">새로운 결정이 수집되면 여기에 표시됩니다</p>
        </div>
      )}
    </div>
  )
}
