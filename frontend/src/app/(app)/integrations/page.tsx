'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { integrationsApi } from '@/lib/api/integrations';
import { JobStatusIndicator } from '@/components/shared/JobStatusIndicator';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { IntegrationType, IntegrationStatus } from '@/lib/types/api';
import { RefreshCw, Link2Off, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react';

const integrationMeta: Record<
  IntegrationType,
  { label: string; icon: string; description: string }
> = {
  google_drive: {
    label: 'Google Drive',
    icon: '📁',
    description: '문서, 스프레드시트, 슬라이드, PDF',
  },
  gmail: {
    label: 'Gmail',
    icon: '📧',
    description: '회사 도메인 이메일 스레드',
  },
  slack: {
    label: 'Slack',
    icon: '💬',
    description: '공개/비공개 채널 메시지',
  },
  google_calendar: {
    label: 'Google Calendar',
    icon: '📆',
    description: '회의 일정 및 이벤트',
  },
};

const statusIcon: Record<IntegrationStatus, React.ReactNode> = {
  connected: <CheckCircle className="w-4 h-4 text-green-500" />,
  disconnected: <XCircle className="w-4 h-4 text-gray-400" />,
  error: <AlertCircle className="w-4 h-4 text-red-500" />,
  syncing: <Loader className="w-4 h-4 text-blue-500 animate-spin" />,
};
const statusLabel: Record<IntegrationStatus, string> = {
  connected: '연결됨',
  disconnected: '연결 안됨',
  error: '오류',
  syncing: '동기화 중',
};

export default function IntegrationsPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const orgId = user?.organization_id ?? '';
  const [jobIds, setJobIds] = useState<Record<string, string>>({});
  const [confirmDisconnect, setConfirmDisconnect] = useState<IntegrationType | null>(null);

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations', orgId],
    queryFn: () => integrationsApi.list(orgId),
    enabled: !!orgId,
    refetchInterval: 10_000,
  });

  const syncMutation = useMutation({
    mutationFn: (type: IntegrationType) => integrationsApi.sync(type),
    onSuccess: (data, type) => {
      setJobIds((prev) => ({ ...prev, [type]: data.job_id }));
      qc.invalidateQueries({ queryKey: ['integrations', orgId] });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (type: IntegrationType) => integrationsApi.disconnect(type),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations', orgId] });
      setConfirmDisconnect(null);
    },
  });

  // 연결되지 않은 타입은 기본 카드로 표시
  const allTypes: IntegrationType[] = ['google_drive', 'gmail', 'slack', 'google_calendar'];

  return (
    <div className="max-w-4xl space-y-5">
      <h1 className="text-2xl font-semibold text-gray-900">데이터 연동</h1>
      <p className="text-sm text-gray-500">외부 데이터 소스를 연결하고 동기화하세요.</p>

      {isLoading && <p className="text-sm text-gray-500">불러오는 중...</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {allTypes.map((type) => {
          const meta = integrationMeta[type];
          const integration = integrations?.find((i) => i.type === type);
          const status: IntegrationStatus = integration?.status ?? 'disconnected';
          const jobId = jobIds[type] ?? null;

          return (
            <div key={type} className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{meta.icon}</span>
                  <div>
                    <p className="font-medium text-gray-800">{meta.label}</p>
                    <p className="text-xs text-gray-500">{meta.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {statusIcon[status]}
                  <span className="text-xs text-gray-600">{statusLabel[status]}</span>
                </div>
              </div>

              {integration?.last_synced_at && (
                <p className="text-xs text-gray-400">
                  마지막 동기화:{' '}
                  {format(new Date(integration.last_synced_at), 'MM.dd HH:mm', { locale: ko })}
                </p>
              )}
              {integration?.error_message && (
                <p className="text-xs text-red-500">{integration.error_message}</p>
              )}

              <JobStatusIndicator jobId={jobId} />

              <div className="flex gap-2">
                <button
                  onClick={() => syncMutation.mutate(type)}
                  disabled={syncMutation.isPending || status === 'syncing'}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  지금 동기화
                </button>
                {status !== 'disconnected' && (
                  <button
                    onClick={() => setConfirmDisconnect(type)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded-md hover:bg-red-50 transition-colors"
                  >
                    <Link2Off className="w-3.5 h-3.5" />
                    연결 해제
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 연결 해제 확인 모달 */}
      {confirmDisconnect && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-2">연결 해제</h2>
            <p className="text-sm text-gray-600 mb-5">
              {integrationMeta[confirmDisconnect].label} 연결을 해제하시겠습니까?
              해제 후에는 해당 소스의 새로운 데이터가 동기화되지 않습니다.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDisconnect(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={() => disconnectMutation.mutate(confirmDisconnect)}
                disabled={disconnectMutation.isPending}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {disconnectMutation.isPending ? '해제 중...' : '해제'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
