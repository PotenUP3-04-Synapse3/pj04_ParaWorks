'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiFetch } from '@/lib/api';

interface Integration {
  id: string;
  service_type: string;
  status: string;
  last_synced_at: string | null;
}

const SERVICE_LABELS: Record<string, string> = {
  gmail: 'Gmail',
  slack: 'Slack',
  google_drive: 'Google Drive',
  github: 'GitHub',
  google_calendar: 'Google Calendar',
};

// Google OAuth를 사용하는 서비스
const GOOGLE_OAUTH_SERVICES = new Set(['google_drive', 'gmail', 'google_calendar']);

export default function IntegrationsPage() {
  return (
    <Suspense fallback={<div className="p-8">로딩 중...</div>}>
      <IntegrationsContent />
    </Suspense>
  );
}

function IntegrationsContent() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    apiFetch<Integration[]>('/integrations').then(setIntegrations);
  }, []);

  // OAuth 콜백 후 리디렉트 결과 처리
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');
    if (connected) {
      setToast(`${SERVICE_LABELS[connected] ?? connected} 연결 완료!`);
      apiFetch<Integration[]>('/integrations').then(setIntegrations);
      window.history.replaceState({}, '', '/integrations');
    } else if (error) {
      setToast(`연결 실패: ${error}`);
      window.history.replaceState({}, '', '/integrations');
    }
  }, [searchParams]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const disconnect = async (id: string) => {
    await apiFetch(`/integrations/${id}`, { method: 'DELETE' });
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
    setToast('연결 해제되었습니다.');
  };

  const connect = async (type: string) => {
    setConnecting(type);
    try {
      if (GOOGLE_OAUTH_SERVICES.has(type)) {
        // 백엔드에서 Google OAuth URL 받아서 이동
        const { url } = await apiFetch<{ url: string }>(
          `/integrations/google/authorize?service=${type}`
        );
        window.location.href = url;
        return;
      }
      // Slack은 별도 OAuth URL 사용
      if (type === 'slack') {
        const clientId = process.env.NEXT_PUBLIC_SLACK_CLIENT_ID;
        const redirectUri = encodeURIComponent(
          `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/webhooks/slack/oauth/callback`
        );
        window.location.href =
          `https://slack.com/oauth/v2/authorize?client_id=${clientId}&scope=channels:read,channels:history,chat:write&redirect_uri=${redirectUri}`;
        return;
      }
      setToast(`${SERVICE_LABELS[type]} 연동은 아직 준비 중입니다.`);
    } finally {
      setConnecting(null);
    }
  };

  const connected = new Set(integrations.map((i) => i.service_type));

  return (
    <div className="p-8">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-gray-800 text-white text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
      <h1 className="text-2xl font-bold mb-6">연동 서비스</h1>
      <div className="grid gap-4">
        {Object.entries(SERVICE_LABELS).map(([type, label]) => {
          const intg = integrations.find((i) => i.service_type === type);
          const isConnecting = connecting === type;
          return (
            <div key={type} className="bg-white rounded-xl shadow px-6 py-4 flex items-center justify-between">
              <div>
                <p className="font-semibold">{label}</p>
                {intg && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {intg.last_synced_at
                      ? `마지막 동기화: ${intg.last_synced_at.slice(0, 16)}`
                      : '동기화 대기 중'}
                  </p>
                )}
              </div>
              {intg ? (
                <div className="flex items-center gap-3">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">연결됨</span>
                  <button
                    onClick={() => disconnect(intg.id)}
                    className="text-xs text-red-500 hover:underline"
                  >
                    연결 해제
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => connect(type)}
                  disabled={isConnecting}
                  className="text-xs bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition-colors"
                >
                  {isConnecting ? '연결 중...' : '연결하기'}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
