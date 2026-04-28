'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { searchApi } from '@/lib/api/search';
import { useAuthStore } from '@/lib/stores/authStore';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';
import { ConfidenceBar } from '@/components/shared/ConfidenceBar';
import type { SearchResponse, SourceSnippet } from '@/lib/types/api';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

export default function SearchPage() {
  const user = useAuthStore((s) => s.user);
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const [openSnippet, setOpenSnippet] = useState<string | null>(null);

  const { mutate, data, isPending, isError } = useMutation<SearchResponse, Error>({
    mutationFn: () =>
      searchApi.query({
        query,
        org_id: user!.organization_id,
        user_id: user!.id,
      }),
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) mutate();
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">지식 검색</h1>

      {/* 검색 폼 */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="무엇이든 물어보세요 — 의사결정 이유, 프로젝트 히스토리..."
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isPending || !query.trim()}
          className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? '검색 중...' : '검색'}
        </button>
      </form>

      {isError && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3">
          검색 중 오류가 발생했습니다.
        </p>
      )}

      {data && (
        <div className="space-y-5">
          {/* 답변 */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-gray-800">AI 답변</h2>
              <div className="w-36">
                <ConfidenceBar score={data.confidence_score} />
              </div>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {data.answer}
            </p>
          </div>

          {/* 소스 */}
          {data.sources.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100">
                <h2 className="font-medium text-gray-800">소스 ({data.sources.length})</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {data.sources.map((src) => (
                  <SourceRow
                    key={src.source_id}
                    src={src}
                    open={openSnippet === src.source_id}
                    onToggle={() =>
                      setOpenSnippet((prev) =>
                        prev === src.source_id ? null : src.source_id,
                      )
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {/* 관련 의사결정 */}
          {data.related_decisions.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100">
                <h2 className="font-medium text-gray-800">관련 의사결정</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {data.related_decisions.map((d) => (
                  <div key={d.id} className="px-5 py-3 flex items-center justify-between">
                    <p className="text-sm text-gray-800">{d.title}</p>
                    <ReviewStatusBadge status={d.review_status} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SourceRow({
  src,
  open,
  onToggle,
}: {
  src: SourceSnippet;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="px-5 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-800 truncate">{src.title}</p>
            {src.url && (
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-shrink-0 text-gray-400 hover:text-blue-600"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">관련도 {Math.round(src.score * 100)}%</p>
        </div>
        <button
          onClick={onToggle}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600"
          aria-label="스니펫 펼치기"
        >
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>
      {open && (
        <p className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2 leading-relaxed">
          {src.snippet}
        </p>
      )}
    </div>
  );
}
