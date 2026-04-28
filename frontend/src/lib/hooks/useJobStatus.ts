'use client';

import { useEffect, useRef, useState } from 'react';
import type { SSEEvent, SSEEventType } from '@/lib/types/api';

export type JobStatusState = {
  status: SSEEventType | 'idle';
  pct: number;
  message: string;
  error: string | null;
};

/**
 * SSE 기반 job 진행률 훅
 * GET /api/v1/stream/job-status?job_id=<id> 구독
 */
export function useJobStatus(jobId: string | null): JobStatusState {
  const [state, setState] = useState<JobStatusState>({
    status: 'idle',
    pct: 0,
    message: '',
    error: null,
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const baseUrl =
      process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    const url = `${baseUrl}/api/v1/stream/job-status?job_id=${encodeURIComponent(jobId)}`;

    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e: MessageEvent<string>) => {
      try {
        const event = JSON.parse(e.data) as SSEEvent;
        switch (event.type) {
          case 'connected':
            setState((s) => ({ ...s, status: 'connected' }));
            break;
          case 'progress':
            setState({
              status: 'progress',
              pct: event.pct ?? 0,
              message: event.message ?? '',
              error: null,
            });
            break;
          case 'done':
            setState({ status: 'done', pct: 100, message: event.message ?? '완료', error: null });
            es.close();
            break;
          case 'error':
            setState({ status: 'error', pct: 0, message: '', error: event.message ?? '오류' });
            es.close();
            break;
        }
      } catch {
        // JSON 파싱 실패 (ping 메시지 등) — 무시
      }
    };

    es.onerror = () => {
      setState((s) => ({
        ...s,
        status: 'error',
        error: '연결이 끊어졌습니다.',
      }));
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [jobId]);

  return state;
}
