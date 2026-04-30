import { cn } from '@/lib/utils'

type Level = 'public' | 'team' | 'restricted'

const CONFIG: Record<Level, { label: string; cls: string }> = {
  public: { label: '전사 공개', cls: 'bg-green-100 text-green-800 border border-green-200' },
  team: { label: '팀 공개', cls: 'bg-blue-100 text-blue-800 border border-blue-200' },
  restricted: { label: '제한', cls: 'bg-red-100 text-red-800 border border-red-200' },
}

interface PermissionBadgeProps {
  level: string
  className?: string
}

export function PermissionBadge({ level, className }: PermissionBadgeProps) {
  const cfg = CONFIG[level as Level] ?? { label: level, cls: 'bg-gray-100 text-gray-700' }
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        cfg.cls,
        className,
      )}
    >
      {cfg.label}
    </span>
  )
}
