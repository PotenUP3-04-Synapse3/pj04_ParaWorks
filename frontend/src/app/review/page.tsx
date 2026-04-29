'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

interface ReviewItem {
  id: string;
  item_type: string;
  status: string;
  content_snapshot: Record<string, unknown> | null;
  created_by_agent: string | null;
  rejection_reason: string | null;
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () =>
    apiFetch<ReviewItem[]>('/review-queue?item_status=pending').then(setItems);

  useEffect(() => { load(); }, []);

  const accept = async (id: string) => {
    setLoading(true);
    await apiFetch(`/review-queue/${id}/accept`, { method: 'POST' });
    await load();
    setLoading(false);
  };

  const reject = async (id: string) => {
    const reason = window.prompt('반려 사유를 입력하세요 (선택)');
    setLoading(true);
    await apiFetch(`/review-queue/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
    await load();
    setLoading(false);
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">검토 대기 목록</h1>
      <div className="space-y-4">
        {items.length === 0 && <p className="text-gray-400">대기 중인 항목이 없습니다.</p>}
        {items.map((item) => (
          <div key={item.id} className="bg-white rounded-xl shadow px-6 py-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <p className="text-xs text-gray-400 uppercase mb-1">{item.item_type}</p>
                <pre className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-4">
                  {JSON.stringify(item.content_snapshot, null, 2)}
                </pre>
                {item.created_by_agent && (
                  <p className="text-xs text-gray-400 mt-2">생성 에이전트: {item.created_by_agent}</p>
                )}
              </div>
              <div className="flex gap-2 ml-4 shrink-0">
                <button
                  onClick={() => accept(item.id)}
                  disabled={loading}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  승인
                </button>
                <button
                  onClick={() => reject(item.id)}
                  disabled={loading}
                  className="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
                >
                  반려
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
