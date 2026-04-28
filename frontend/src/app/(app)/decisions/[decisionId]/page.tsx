'use client';

import { use } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { decisionsApi } from '@/lib/api/decisions';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';
import { ConfidenceBar } from '@/components/shared/ConfidenceBar';
import { reviewApi } from '@/lib/api/review';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ExternalLink, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function DecisionDetailPage({
  params,
}: {
  params: Promise<{ decisionId: string }>;
}) {
  const { decisionId } = use(params);
  const qc = useQueryClient();

  const { data: decision, isLoading } = useQuery({
    queryKey: ['decision', decisionId],
    queryFn: () => decisionsApi.get(decisionId),
  });

  const approveMutation = useMutation({
    mutationFn: () => reviewApi.approve(decisionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['decision', decisionId] }),
  });

  const rejectMutation = useMutation({
    mutationFn: () => reviewApi.reject(decisionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['decision', decisionId] }),
  });

  if (isLoading) {
    return <p className="text-sm text-gray-500">불러오는 중...</p>;
  }
  if (!decision) {
    return <p className="text-sm text-red-600">의사결정을 찾을 수 없습니다.</p>;
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/decisions" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 flex-1">{decision.title}</h1>
        <ReviewStatusBadge status={decision.review_status} />
      </div>

      {/* 메타 정보 */}
      <div className="grid grid-cols-2 gap-4 bg-white rounded-xl border border-gray-200 p-5">
        <Field label="의사결정자" value={decision.decision_maker} />
        <Field
          label="결정일"
          value={
            decision.decided_at
              ? format(new Date(decision.decided_at), 'yyyy년 MM월 dd일', { locale: ko })
              : '—'
          }
        />
        <Field label="권한 수준" value={decision.permission_level} />
        <div>
          <p className="text-xs text-gray-500 mb-1">신뢰도</p>
          <div className="w-36">
            <ConfidenceBar score={decision.confidence_score} />
          </div>
        </div>
      </div>

      {/* 요약 / 근거 */}
      {decision.summary && (
        <Section title="요약">
          <p className="text-sm text-gray-700 leading-relaxed">{decision.summary}</p>
        </Section>
      )}
      {decision.rationale && (
        <Section title="근거">
          <p className="text-sm text-gray-700 leading-relaxed">{decision.rationale}</p>
        </Section>
      )}

      {/* 대안 / 제약 */}
      {decision.alternatives_considered?.length ? (
        <Section title="검토된 대안">
          <ul className="list-disc list-inside space-y-1">
            {decision.alternatives_considered.map((a, i) => (
              <li key={i} className="text-sm text-gray-700">{a}</li>
            ))}
          </ul>
        </Section>
      ) : null}
      {decision.constraints?.length ? (
        <Section title="제약사항">
          <ul className="list-disc list-inside space-y-1">
            {decision.constraints.map((c, i) => (
              <li key={i} className="text-sm text-gray-700">{c}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {/* 참여자 */}
      {decision.stakeholders?.length ? (
        <Section title="이해관계자">
          <div className="flex flex-wrap gap-2">
            {decision.stakeholders.map((s, i) => (
              <span key={i} className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-700">
                {s}
              </span>
            ))}
          </div>
        </Section>
      ) : null}

      {/* 소스 링크 */}
      {decision.source_links?.length ? (
        <Section title="소스 링크">
          <div className="space-y-1">
            {decision.source_links.map((url, i) => (
              <a
                key={i}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {url}
              </a>
            ))}
          </div>
        </Section>
      ) : null}

      {/* 리뷰 액션 */}
      {decision.review_status === 'pending' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center gap-3">
          <p className="text-sm text-yellow-800 flex-1">이 의사결정은 AI 초안입니다. 검토 후 승인 또는 거부하세요.</p>
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={rejectMutation.isPending}
            className="px-4 py-2 text-sm border border-red-300 text-red-600 rounded-md hover:bg-red-50 disabled:opacity-50"
          >
            거부
          </button>
          <button
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            승인
          </button>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-gray-800 mt-0.5 capitalize">{value}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h2 className="font-medium text-gray-800 mb-3">{title}</h2>
      {children}
    </div>
  );
}
