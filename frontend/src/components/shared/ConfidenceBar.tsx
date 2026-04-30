import { cn } from '@/lib/utils'

interface ConfidenceBarProps {
  score: number  // 0.0 - 1.0
  showLabel?: boolean
  className?: string
}

export function ConfidenceBar({ score, showLabel = true, className }: ConfidenceBarProps) {
  const pct = Math.round(score * 100)

  const color =
    pct >= 80
      ? 'bg-green-500'
      : pct >= 60
        ? 'bg-yellow-400'
        : pct >= 40
          ? 'bg-orange-400'
          : 'bg-red-400'

  const label =
    pct >= 80 ? '높음' : pct >= 60 ? '보통' : pct >= 40 ? '낮음' : '매우 낮음'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="h-2 w-24 rounded-full bg-gray-200 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-gray-500">
          {pct}% ({label})
        </span>
      )}
    </div>
  )
}
