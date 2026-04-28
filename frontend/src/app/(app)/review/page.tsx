'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { reviewApi } from '@/lib/api/review';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';
import { ConfidenceBar } from '@/components/shared/ConfidenceBar';
import { JobStatusIndicator } from '@/components/shared/JobStatusIndicator';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ExternalLink, Check, X } from 'lucide-react';

export default function ReviewPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const orgId = user?.organization_id ?? '';
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { data: items, isLoading } = useQuery({
    queryKey: ['review', orgId],
    queryFn: () => reviewApi.list(orgId, 'pending'),
    enabled: !!orgId,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => reviewApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review', orgId] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => reviewApi.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review', orgId] }),
  });

  return (
    <div className="max-w-4xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">검토 대기 큐</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            AI가 추출한 의사결정 초안을 검토하고 승인 또는 거부하세요.
          </p>
        </div>
        {items && (
          <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
            {items.length}건 대기
          </span>
        )}
      </div>

      {/* SSE 진행 상태 */}
      <JobStatusIndicator jobId={activeJobId} />

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}
      {!isLoading && !items?.length && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-8 text-center">
          <p className="text-green-700 font-medium">검토 대기 항목이 없습니다.</p>
          <p className="text-green-600 text-sm mt-1">모든 AI 초안이 처리되었습니다.</p>
        </div>
      )}

      <div className="space-y-3">
        {items?.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-medium text-gray-800">{item.title}</p>
                  <ReviewStatusBadge status={item.review_status as 'pending'} />
                </div>
                {item.summary && (
                  <p className="text-sm text-gray-600 line-clamp-2">{item.summary}</p>
                )}
                <div className="flex items-center gap-4 mt-2">
                  <div className="w-28">
                    <ConfidenceBar score={item.confidence_score} />
                  </div>
                  <span className="text-xs text-gray-400">
                    {format(new Date(item.created_at), 'yyyy.MM.dd HH:mm', { locale: ko })}
                  </span>
                </div>
                {item.source_links.length > 0 && (
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {item.source_links.slice(0, 3).map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        소스 {i + 1}
                      </a>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => rejectMutation.mutate(item.id)}
                  disabled={rejectMutation.isPending}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded-md hover:bg-red-50 disabled:opacity-50"
                >
                  <X className="w-3.5 h-3.5" /> 거부
                </button>
                <button
                  onClick={() => approveMutation.mutate(item.id)}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" /> 승인
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
