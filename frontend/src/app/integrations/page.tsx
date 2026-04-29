'use client';

import { useEffect, useState } from 'react';
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

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);

  useEffect(() => {
    apiFetch<Integration[]>('/integrations').then(setIntegrations);
  }, []);

  const disconnect = async (id: string) => {
    await apiFetch(`/integrations/${id}`, { method: 'DELETE' });
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
  };

  const connected = new Set(integrations.map((i) => i.service_type));

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">연동 서비스</h1>
      <div className="grid gap-4">
        {Object.entries(SERVICE_LABELS).map(([type, label]) => {
          const intg = integrations.find((i) => i.service_type === type);
          return (
            <div key={type} className="bg-white rounded-xl shadow px-6 py-4 flex items-center justify-between">
              <div>
                <p className="font-semibold">{label}</p>
                {intg && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {intg.last_synced_at ? `마지막 동기화: ${intg.last_synced_at.slice(0, 16)}` : '동기화 대기 중'}
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
                <span className="text-xs bg-gray-100 text-gray-400 px-2 py-1 rounded-full">미연결</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
