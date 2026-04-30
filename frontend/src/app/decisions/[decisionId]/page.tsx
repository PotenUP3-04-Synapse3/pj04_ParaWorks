'use client'

import { use, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { ConfidenceBar } from '@/components/shared/ConfidenceBar'
import { PermissionBadge } from '@/components/shared/PermissionBadge'
import { SourceEvidenceDrawer } from '@/components/shared/SourceEvidenceDrawer'
import { useAuthStore } from '@/lib/stores/authStore'
import Link from 'next/link'

interface DecisionDetail {
  id: string
  title: string
  decision_summary?: string
  situation?: string
  reason?: string
  alternatives_considered?: Array<{ option: string; pros: string[]; cons: string[] }>
  constraints?: string
  final_decision?: string
  decision_maker?: string
  participants?: string[]
  decided_at?: string
  confidence_score?: number
  permission_level: string
  review_status: string
  source_links?: unknown[]
  source_snippets?: Array<{
    id?: string; text: string; source_url: string; source_type: string; author?: string
  }>
  tags?: string[]
  business_domain?: string
  related_project_id?: string
}

export default function DecisionDetailPage({
  params,
}: {
  params: Promise<{ decisionId: string }>
}) {
  const { decisionId } = use(params)
  const user = useAuthStore((s) => s.user)
  const qc = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)

  const { data: decision, isLoading } = useQuery<DecisionDetail>({
    queryKey: ['decision', decisionId],
    queryFn: () => api.get<DecisionDetail>(`/decisions/${decisionId}`),
  })

  const approveMutation = useMutation({
    mutationFn: () => api.post(`/decisions/${decisionId}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['decision', decisionId] }),
  })

  const rejectMutation = useMutation({
    mutationFn: () => api.post(`/decisions/${decisionId}/reject`, { reason: rejectReason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['decision', decisionId] })
      setShowRejectForm(false)
    },
  })

  const isManager = user?.role === 'admin' || user?.role === 'manager'

  if (isLoading) return <div className="p-8 text-center text-gray-400">로딩 중...</div>
  if (!decision) return <div className="p-8 text-center text-red-500">결정을 찾을 수 없습니다.</div>

  const snippets = (decision.source_snippets ?? []).map((s, i) => ({
    id: s.id ?? `${i}`,
    text: s.text,
    source_url: s.source_url,
    source_type: s.source_type,
    author: s.author,
  }))

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href="/decisions" className="hover:text-blue-600">의사결정</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium truncate">{decision.title}</span>
      </div>

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-xl font-bold text-gray-900">{decision.title}</h1>
          <PermissionBadge level={decision.permission_level} />
        </div>
        {decision.decision_summary && (
          <p className="mt-2 text-gray-600">{decision.decision_summary}</p>
        )}
        <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-gray-500">
          {typeof decision.confidence_score === 'number' && (
            <ConfidenceBar score={decision.confidence_score} />
          )}
          {decision.decided_at && (
            <span>결정일: {new Date(decision.decided_at).toLocaleDateString('ko-KR')}</span>
          )}
          {decision.decision_maker && <span>결정자: {decision.decision_maker}</span>}
          {decision.business_domain && (
            <span className="rounded-full px-2 py-0.5 bg-purple-100 text-purple-700 text-xs">
              {decision.business_domain}
            </span>
          )}
        </div>

        {/* Manager actions */}
        {isManager && decision.review_status === 'pending_review' && (
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-60"
            >
              승인
            </button>
            <button
              onClick={() => setShowRejectForm(true)}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              반려
            </button>
          </div>
        )}
        {showRejectForm && (
          <div className="mt-3 space-y-2">
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="반려 사유를 입력하세요..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none"
              rows={3}
            />
            <div className="flex gap-2">
              <button
                onClick={() => rejectMutation.mutate()}
                disabled={!rejectReason.trim() || rejectMutation.isPending}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-700 disabled:opacity-60"
              >
                반려 확인
              </button>
              <button onClick={() => setShowRejectForm(false)} className="text-xs text-gray-400 hover:text-gray-600">취소</button>
            </div>
          </div>
        )}
      </div>

      {/* Decision context */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
        {decision.situation && (
          <Section title="상황 (Situation)" content={decision.situation} />
        )}
        {decision.reason && (
          <Section title="결정 이유" content={decision.reason} />
        )}
        {decision.constraints && (
          <Section title="제약 조건" content={decision.constraints} />
        )}
        {decision.final_decision && (
          <Section title="최종 결정" content={decision.final_decision} highlighted />
        )}
      </div>

      {/* Alternatives */}
      {decision.alternatives_considered && decision.alternatives_considered.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">검토한 대안</h2>
          <div className="space-y-4">
            {decision.alternatives_considered.map((alt, i) => (
              <div key={i} className="rounded-lg bg-gray-50 p-4">
                <p className="font-medium text-gray-800 mb-2">{alt.option}</p>
                <div className="grid grid-cols-2 gap-3">
                  {alt.pros.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-green-600 mb-1">장점</p>
                      <ul className="space-y-1">
                        {alt.pros.map((p, j) => <li key={j} className="text-xs text-gray-600">+ {p}</li>)}
                      </ul>
                    </div>
                  )}
                  {alt.cons.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-red-500 mb-1">단점</p>
                      <ul className="space-y-1">
                        {alt.cons.map((c, j) => <li key={j} className="text-xs text-gray-600">- {c}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Participants & sources */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        {decision.participants && decision.participants.length > 0 && (
          <div className="mb-4">
            <p className="text-sm font-semibold text-gray-700 mb-2">참여자</p>
            <div className="flex flex-wrap gap-2">
              {decision.participants.map((p) => (
                <span key={p} className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">{p}</span>
              ))}
            </div>
          </div>
        )}
        {snippets.length > 0 && (
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-sm text-blue-600 hover:underline"
          >
            출처 및 근거 보기 ({snippets.length}개)
          </button>
        )}
      </div>

      <SourceEvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        snippets={snippets}
      />
    </div>
  )
}

function Section({ title, content, highlighted = false }: { title: string; content: string; highlighted?: boolean }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</h3>
      <p className={`text-sm leading-relaxed whitespace-pre-wrap ${highlighted ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
        {content}
      </p>
    </div>
  )
}
