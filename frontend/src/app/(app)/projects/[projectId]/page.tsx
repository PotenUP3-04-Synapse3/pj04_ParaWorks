'use client';

import { use } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { decisionsApi } from '@/lib/api/decisions';
import Link from 'next/link';
import { ArrowLeft, Clock, GitBranch } from 'lucide-react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';

const statusLabel: Record<string, string> = {
  active: '진행 중',
  completed: '완료',
  archived: '보관됨',
};

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  });

  const { data: decisions } = useQuery({
    queryKey: ['project-decisions', projectId],
    queryFn: () => decisionsApi.list('', { limit: 20 }),
    enabled: !!project,
  });

  if (isLoading) return <p className="text-sm text-gray-500">불러오는 중...</p>;
  if (!project) return <p className="text-sm text-red-600">프로젝트를 찾을 수 없습니다.</p>;

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/projects" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 flex-1">{project.name}</h1>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
          {statusLabel[project.status] ?? project.status}
        </span>
      </div>

      {/* 프로젝트 정보 */}
      <div className="grid grid-cols-2 gap-4 bg-white rounded-xl border border-gray-200 p-5">
        {project.description && (
          <div className="col-span-2">
            <p className="text-xs text-gray-500">설명</p>
            <p className="text-sm text-gray-700 mt-0.5">{project.description}</p>
          </div>
        )}
        {project.started_at && (
          <div>
            <p className="text-xs text-gray-500">시작일</p>
            <p className="text-sm font-medium text-gray-800 mt-0.5">
              {format(new Date(project.started_at), 'yyyy.MM.dd', { locale: ko })}
            </p>
          </div>
        )}
        {project.ended_at && (
          <div>
            <p className="text-xs text-gray-500">종료일</p>
            <p className="text-sm font-medium text-gray-800 mt-0.5">
              {format(new Date(project.ended_at), 'yyyy.MM.dd', { locale: ko })}
            </p>
          </div>
        )}
      </div>

      {/* 탭 링크 */}
      <div className="flex gap-2">
        <Link
          href={`/projects/${projectId}/timeline`}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 transition-colors"
        >
          <Clock className="w-4 h-4" /> 타임라인
        </Link>
        <Link
          href={`/projects/${projectId}/history`}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 transition-colors"
        >
          <GitBranch className="w-4 h-4" /> 히스토리
        </Link>
      </div>

      {/* 관련 의사결정 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100">
          <h2 className="font-medium text-gray-800">관련 의사결정</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {!decisions?.length && (
            <p className="px-5 py-4 text-sm text-gray-500">관련 의사결정이 없습니다.</p>
          )}
          {decisions?.map((d) => (
            <Link
              key={d.id}
              href={`/decisions/${d.id}`}
              className="flex items-center justify-between px-5 py-3 hover:bg-gray-50"
            >
              <p className="text-sm text-gray-800">{d.title}</p>
              <ReviewStatusBadge status={d.review_status} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
