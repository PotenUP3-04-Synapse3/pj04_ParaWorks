'use client'

import { useJobStatus } from '@/lib/hooks/useJobStatus'
import { cn } from '@/lib/utils'

interface JobStatusIndicatorProps {
  taskId: string | null
  className?: string
}

const STATUS_CONFIG = {
  PENDING: { label: '대기 중', cls: 'bg-gray-100 text-gray-600' },
  STARTED: { label: '시작됨', cls: 'bg-blue-100 text-blue-700' },
  PROGRESS: { label: '진행 중', cls: 'bg-blue-100 text-blue-700' },
  SUCCESS: { label: '완료', cls: 'bg-green-100 text-green-700' },
  done: { label: '완료', cls: 'bg-green-100 text-green-700' },
  FAILURE: { label: '실패', cls: 'bg-red-100 text-red-700' },
  error: { label: '오류', cls: 'bg-red-100 text-red-700' },
  timeout: { label: '타임아웃', cls: 'bg-orange-100 text-orange-700' },
}

export function JobStatusIndicator({ taskId, className }: JobStatusIndicatorProps) {
  const { data, isComplete } = useJobStatus(taskId)

  if (!taskId || !data) return null

  const cfg = STATUS_CONFIG[data.status as keyof typeof STATUS_CONFIG] ?? {
    label: data.status,
    cls: 'bg-gray-100 text-gray-600',
  }

  const isRunning = !isComplete && ['PENDING', 'STARTED', 'PROGRESS'].includes(data.status)

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        cfg.cls,
        className,
      )}
    >
      {isRunning && (
        <svg
          className="h-3 w-3 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {cfg.label}
      {typeof data.progress === 'number' && isRunning && ` (${data.progress}%)`}
    </div>
  )
}
