'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { projectsApi } from '@/lib/api/projects';
import Link from 'next/link';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Plus, ChevronRight } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import type { ProjectCreate, ProjectStatus } from '@/lib/types/api';

const statusLabel: Record<ProjectStatus, string> = {
  active: '진행 중',
  completed: '완료',
  archived: '보관됨',
};
const statusColor: Record<ProjectStatus, string> = {
  active: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  archived: 'bg-gray-100 text-gray-500',
};

const createSchema = z.object({
  name: z.string().min(1, '프로젝트명을 입력하세요'),
  description: z.string().optional(),
  status: z.enum(['active', 'completed', 'archived']),
  started_at: z.string().optional(),
  ended_at: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

export default function ProjectsPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const orgId = user?.organization_id ?? '';
  const [showCreate, setShowCreate] = useState(false);

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects', orgId],
    queryFn: () => projectsApi.list(orgId),
    enabled: !!orgId,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<CreateForm>({ resolver: zodResolver(createSchema) as any, defaultValues: { status: 'active' } });

  const createMutation = useMutation({
    mutationFn: (body: CreateForm) =>
      projectsApi.create({ ...body, organization_id: orgId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects', orgId] });
      setShowCreate(false);
      reset();
    },
  });

  return (
    <div className="max-w-4xl space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">프로젝트</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> 새 프로젝트
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}
      {!isLoading && !projects?.length && (
        <p className="text-sm text-gray-500">프로젝트가 없습니다.</p>
      )}

      <div className="grid grid-cols-1 gap-3">
        {projects?.map((p) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="flex items-center gap-4 bg-white rounded-xl border border-gray-200 px-5 py-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-800">{p.name}</p>
              {p.description && (
                <p className="text-sm text-gray-500 truncate mt-0.5">{p.description}</p>
              )}
              {p.started_at && (
                <p className="text-xs text-gray-400 mt-1">
                  {format(new Date(p.started_at), 'yyyy.MM.dd', { locale: ko })}
                  {p.ended_at && ` ~ ${format(new Date(p.ended_at), 'yyyy.MM.dd', { locale: ko })}`}
                </p>
              )}
            </div>
            <span
              className={`flex-shrink-0 px-2 py-1 rounded-full text-xs font-medium ${statusColor[p.status]}`}
            >
              {statusLabel[p.status]}
            </span>
            <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
          </Link>
        ))}
      </div>

      {/* 생성 모달 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">새 프로젝트 생성</h2>
            <form onSubmit={handleSubmit((v) => createMutation.mutate(v as CreateForm))} className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-700">프로젝트명 *</label>
                <input {...register('name')} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                {errors.name && <p className="text-xs text-red-600 mt-0.5">{errors.name.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">설명</label>
                <textarea {...register('description')} rows={2} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium text-gray-700">시작일</label>
                  <input type="date" {...register('started_at')} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">종료일</label>
                  <input type="date" {...register('ended_at')} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" onClick={() => { setShowCreate(false); reset(); }} className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50">취소</button>
                <button type="submit" disabled={isSubmitting || createMutation.isPending} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">
                  {createMutation.isPending ? '생성 중...' : '생성'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
