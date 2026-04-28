'use client';

import { use } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

const sourceIcon: Record<string, string> = {
  google_drive: '📄',
  gmail: '📧',
  slack: '💬',
  google_calendar: '📆',
  decision: '✅',
  manual: '📝',
};

export default function ProjectTimelinePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);

  const { data: events, isLoading } = useQuery({
    queryKey: ['project-timeline', projectId],
    queryFn: () => projectsApi.timeline(projectId),
  });

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <Link href={`/projects/${projectId}`} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">프로젝트 타임라인</h1>
      </div>

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}
      {!isLoading && !events?.length && (
        <p className="text-sm text-gray-500">타임라인 이벤트가 없습니다.</p>
      )}

      <div className="relative">
        {/* 타임라인 선 */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-4">
          {events?.map((evt) => (
            <div key={evt.id} className="relative flex gap-4 pl-12">
              {/* 아이콘 */}
              <div className="absolute left-2.5 top-1 w-5 h-5 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-xs">
                {sourceIcon[evt.source_type] ?? '•'}
              </div>

              <div className="flex-1 bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium text-sm text-gray-800">{evt.title}</p>
                  <span className="text-xs text-gray-400 flex-shrink-0">
                    {format(new Date(evt.occurred_at), 'MM.dd HH:mm', { locale: ko })}
                  </span>
                </div>
                {evt.summary && (
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{evt.summary}</p>
                )}
                {evt.actor_name && (
                  <p className="text-xs text-gray-400 mt-1.5">{evt.actor_name}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
