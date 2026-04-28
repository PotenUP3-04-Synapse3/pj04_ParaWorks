'use client';

import { useJobStatus } from '@/lib/hooks/useJobStatus';
import { cn } from '@/lib/utils';

interface JobStatusIndicatorProps {
  jobId: string | null;
  className?: string;
}

export function JobStatusIndicator({ jobId, className }: JobStatusIndicatorProps) {
  const { status, pct, message, error } = useJobStatus(jobId);

  if (!jobId || status === 'idle') return null;

  return (
    <div
      className={cn(
        'flex flex-col gap-1 p-3 rounded-lg border text-sm',
        status === 'done' && 'border-green-300 bg-green-50',
        status === 'error' && 'border-red-300 bg-red-50',
        (status === 'progress' || status === 'connected') && 'border-blue-300 bg-blue-50',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium">
          {status === 'done' && '✓ 완료'}
          {status === 'error' && '✗ 오류'}
          {(status === 'progress' || status === 'connected') && '⟳ 처리 중...'}
        </span>
        {status === 'progress' && (
          <span className="text-xs text-gray-500">{pct}%</span>
        )}
      </div>
      {message && <p className="text-xs text-gray-600">{message}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {status === 'progress' && (
        <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
