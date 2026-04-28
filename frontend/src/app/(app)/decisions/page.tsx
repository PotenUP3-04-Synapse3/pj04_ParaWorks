'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { decisionsApi } from '@/lib/api/decisions';
import { ReviewStatusBadge } from '@/components/shared/ReviewStatusBadge';
import { ConfidenceBar } from '@/components/shared/ConfidenceBar';
import Link from 'next/link';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Plus } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import type { DecisionRecordCreate } from '@/lib/types/api';

const createSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요'),
  decision_maker: z.string().min(1, '의사결정자를 입력하세요'),
  summary: z.string().optional(),
  rationale: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

export default function DecisionsPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const orgId = user?.organization_id ?? '';
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  const { data: decisions, isLoading } = useQuery({
    queryKey: ['decisions', orgId, statusFilter],
    queryFn: () =>
      decisionsApi.list(orgId, statusFilter ? { review_status: statusFilter } : {}),
    enabled: !!orgId,
  });

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<CreateForm>({ resolver: zodResolver(createSchema) });

  const createMutation = useMutation({
    mutationFn: (body: DecisionRecordCreate) => decisionsApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['decisions', orgId] });
      setShowCreate(false);
      reset();
    },
  });

  return (
    <div className="max-w-5xl space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">의사결정</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> 새 의사결정
        </button>
      </div>

      {/* 필터 */}
      <div className="flex gap-2">
        {['', 'pending', 'confirmed', 'rejected'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {s === '' ? '전체' : s === 'pending' ? '검토 대기' : s === 'confirmed' ? '승인됨' : '거부됨'}
          </button>
        ))}
      </div>

      {/* 테이블 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left border-b border-gray-200">
              <th className="px-4 py-3 font-medium text-gray-600">제목</th>
              <th className="px-4 py-3 font-medium text-gray-600">의사결정자</th>
              <th className="px-4 py-3 font-medium text-gray-600">날짜</th>
              <th className="px-4 py-3 font-medium text-gray-600">신뢰도</th>
              <th className="px-4 py-3 font-medium text-gray-600">상태</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  불러오는 중...
                </td>
              </tr>
            )}
            {!isLoading && !decisions?.length && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  의사결정 기록이 없습니다.
                </td>
              </tr>
            )}
            {decisions?.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <Link
                    href={`/decisions/${d.id}`}
                    className="font-medium text-gray-800 hover:text-blue-600 transition-colors"
                  >
                    {d.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{d.decision_maker}</td>
                <td className="px-4 py-3 text-gray-500">
                  {d.decided_at
                    ? format(new Date(d.decided_at), 'yyyy.MM.dd', { locale: ko })
                    : '—'}
                </td>
                <td className="px-4 py-3 w-28">
                  <ConfidenceBar score={d.confidence_score} />
                </td>
                <td className="px-4 py-3">
                  <ReviewStatusBadge status={d.review_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 생성 모달 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">새 의사결정 등록</h2>
            <form
              onSubmit={handleSubmit((v) => createMutation.mutate(v))}
              className="space-y-3"
            >
              <div>
                <label className="text-sm font-medium text-gray-700">제목 *</label>
                <input {...register('title')} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                {errors.title && <p className="text-xs text-red-600 mt-0.5">{errors.title.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">의사결정자 *</label>
                <input {...register('decision_maker')} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                {errors.decision_maker && <p className="text-xs text-red-600 mt-0.5">{errors.decision_maker.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">요약</label>
                <textarea {...register('summary')} rows={3} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">근거</label>
                <textarea {...register('rationale')} rows={3} className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" onClick={() => { setShowCreate(false); reset(); }} className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50">
                  취소
                </button>
                <button type="submit" disabled={isSubmitting || createMutation.isPending} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">
                  {createMutation.isPending ? '등록 중...' : '등록'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
