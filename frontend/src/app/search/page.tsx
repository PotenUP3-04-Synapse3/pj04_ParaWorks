'use client'

import { useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { ConfidenceBar } from '@/components/shared/ConfidenceBar'
import { PermissionBadge } from '@/components/shared/PermissionBadge'
import { SourceEvidenceDrawer } from '@/components/shared/SourceEvidenceDrawer'

interface SearchResponse {
  query: string
  answer?: string
  key_points: string[]
  related_decisions: string[]
  related_projects: string[]
  caveats: string[]
  confidence_score: number
  needs_human_review: boolean
  source_snippets: Snippet[]
  total_results: number
}

interface Snippet {
  id: string
  text: string
  source_url: string
  source_type: string
  author?: string | null
  similarity: number
  permission_level: string
}

export default function SearchPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const initialQ = searchParams.get('q') ?? ''

  const [inputQuery, setInputQuery] = useState(initialQ)
  const [activeQuery, setActiveQuery] = useState(initialQ)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data, isFetching, isError } = useQuery<SearchResponse>({
    queryKey: ['search', activeQuery],
    queryFn: () =>
      api.post<SearchResponse>('/search', { query: activeQuery, top_k: 10 }),
    enabled: !!activeQuery,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputQuery.trim()) return
    router.push(`/search?q=${encodeURIComponent(inputQuery.trim())}`)
    setActiveQuery(inputQuery.trim())
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">전사 지식 검색</h1>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-8">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="예: 작년에 왜 서비스 A를 선택했나요?"
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
        />
        <button
          type="submit"
          disabled={isFetching}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60 transition-colors"
        >
          {isFetching ? '검색 중...' : '검색'}
        </button>
      </form>

      {isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          검색 중 오류가 발생했습니다. 다시 시도해 주세요.
        </div>
      )}

      {data && (
        <div className="space-y-6">
          {/* Answer card */}
          {data.answer && (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <h2 className="font-semibold text-gray-900">AI 답변</h2>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <ConfidenceBar score={data.confidence_score} />
                  {data.needs_human_review && (
                    <span className="text-xs text-orange-600 font-medium">⚠ 전문가 검토 권장</span>
                  )}
                </div>
              </div>

              <p className="text-gray-800 leading-relaxed mb-4">{data.answer}</p>

              {data.key_points.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">핵심 포인트</p>
                  <ul className="space-y-1">
                    {data.key_points.map((kp, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-blue-500 shrink-0">•</span>
                        {kp}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-wrap gap-3 text-sm">
                {data.related_decisions.length > 0 && (
                  <div>
                    <span className="text-gray-500">관련 결정: </span>
                    {data.related_decisions.map((d, i) => (
                      <span key={i} className="text-blue-600">{d}{i < data.related_decisions.length - 1 ? ', ' : ''}</span>
                    ))}
                  </div>
                )}
                {data.related_projects.length > 0 && (
                  <div>
                    <span className="text-gray-500">관련 프로젝트: </span>
                    {data.related_projects.map((p, i) => (
                      <span key={i} className="text-indigo-600">{p}{i < data.related_projects.length - 1 ? ', ' : ''}</span>
                    ))}
                  </div>
                )}
              </div>

              {data.caveats.length > 0 && (
                <div className="mt-3 text-xs text-gray-400">
                  <span className="font-medium">주의: </span>
                  {data.caveats.join(' / ')}
                </div>
              )}

              {data.source_snippets.length > 0 && (
                <button
                  onClick={() => setDrawerOpen(true)}
                  className="mt-3 text-xs text-blue-600 hover:underline"
                >
                  출처 {data.source_snippets.length}개 보기
                </button>
              )}
            </div>
          )}

          {/* Source snippets */}
          {data.source_snippets.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-3 text-sm">
                검색 결과 ({data.total_results}개)
              </h3>
              <div className="space-y-3">
                {data.source_snippets.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <a
                        href={s.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-xs truncate"
                      >
                        {s.source_url}
                      </a>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs text-gray-400">{Math.round(s.similarity * 100)}%</span>
                        <PermissionBadge level={s.permission_level} />
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">{s.source_type}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-3">{s.text}</p>
                    {s.author && <p className="mt-1 text-xs text-gray-400">작성자: {s.author}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <SourceEvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        snippets={data?.source_snippets ?? []}
      />
    </div>
  )
}
