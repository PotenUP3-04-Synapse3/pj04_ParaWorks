'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { decisionsApi } from '@/lib/api/decisions';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';
import { ConfidenceBar } from '@/components/shared/ConfidenceBar';
import Link from 'next/link';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id ?? '';

  const { data: recentDecisions, isLoading } = useQuery({
    queryKey: ['decisions', orgId],
    queryFn: () => decisionsApi.list(orgId, { limit: 10 }),
    enabled: !!orgId,
  });

  const pendingCount = recentDecisions?.filter((d) => d.review_status === 'pending').length ?? 0;
  const totalCount = recentDecisions?.length ?? 0;

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">대시보드</h1>
        <p className="text-sm text-gray-500 mt-1">
          안녕하세요, {user?.display_name}님
        </p>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="총 의사결정" value={totalCount} color="blue" />
        <StatCard label="검토 대기" value={pendingCount} color="yellow" />
        <StatCard label="지식 자산" value="—" color="green" />
      </div>

      {/* 최근 의사결정 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-medium text-gray-800">최근 의사결정</h2>
          <Link href="/decisions" className="text-sm text-blue-600 hover:underline">
            전체 보기
          </Link>
        </div>
        <div className="divide-y divide-gray-100">
          {isLoading && (
            <p className="px-5 py-4 text-sm text-gray-500">불러오는 중...</p>
          )}
          {!isLoading && !recentDecisions?.length && (
            <p className="px-5 py-4 text-sm text-gray-500">의사결정 기록이 없습니다.</p>
          )}
          {recentDecisions?.map((d) => (
            <Link
              key={d.id}
              href={`/decisions/${d.id}`}
              className="flex items-start gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{d.title}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {d.decision_maker} ·{' '}
                  {d.decided_at
                    ? format(new Date(d.decided_at), 'yyyy.MM.dd', { locale: ko })
                    : '날짜 미상'}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 flex-shrink-0">
                <ReviewStatusBadge status={d.review_status} />
                <div className="w-24">
                  <ConfidenceBar score={d.confidence_score} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* 검토 대기 패널 */}
      {pendingCount > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-5 py-4 flex items-center justify-between">
          <div>
            <p className="font-medium text-yellow-800">
              검토 대기 건이 {pendingCount}건 있습니다
            </p>
            <p className="text-sm text-yellow-700 mt-0.5">
              AI가 추출한 의사결정 초안을 검토하고 승인하세요.
            </p>
          </div>
          <Link
            href="/review"
            className="flex-shrink-0 px-4 py-2 bg-yellow-500 text-white rounded-md text-sm font-medium hover:bg-yellow-600 transition-colors"
          >
            검토하기
          </Link>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color: 'blue' | 'yellow' | 'green';
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    green: 'bg-green-50 text-green-700 border-green-200',
  };
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  );
}
