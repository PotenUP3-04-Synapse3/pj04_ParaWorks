'use client';

import { use } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

export default function ProjectHistoryPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);

  const { data: history, isLoading } = useQuery({
    queryKey: ['project-history', projectId],
    queryFn: () => projectsApi.history(projectId),
  });

  return (
    <div className="max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link href={`/projects/${projectId}`} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">변경 히스토리</h1>
      </div>

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}
      {!isLoading && !history?.length && (
        <p className="text-sm text-gray-500">변경 이력이 없습니다.</p>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left font-medium text-gray-600">항목</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">이벤트</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">일시</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {history?.map((h) => (
              <tr key={h.id}>
                <td className="px-4 py-3 font-medium text-gray-800">{h.title}</td>
                <td className="px-4 py-3 text-gray-600">
                  {h.event_type}
                  {h.diff_from_previous && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-blue-600 hover:underline">
                        변경 내용 보기
                      </summary>
                      <pre className="mt-1 text-xs bg-gray-50 rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap">
                        {h.diff_from_previous}
                      </pre>
                    </details>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {format(new Date(h.occurred_at), 'yyyy.MM.dd HH:mm', { locale: ko })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
