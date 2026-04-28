import { cn } from '@/lib/utils';
import type { ReviewStatus } from '@/lib/types/api';

const statusMap: Record<ReviewStatus, { label: string; className: string }> = {
  pending: {
    label: 'AI 초안 · 검토 필요',
    className: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  },
  confirmed: {
    label: '승인됨',
    className: 'bg-green-100 text-green-800 border-green-300',
  },
  rejected: {
    label: '거부됨',
    className: 'bg-red-100 text-red-800 border-red-300',
  },
  archived: {
    label: '보관됨',
    className: 'bg-gray-100 text-gray-600 border-gray-300',
  },
};

interface ReviewStatusBadgeProps {
  status: ReviewStatus;
  className?: string;
}

export function ReviewStatusBadge({ status, className }: ReviewStatusBadgeProps) {
  const { label, className: statusClass } = statusMap[status] ?? statusMap.pending;
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
        statusClass,
        className,
      )}
    >
      {label}
    </span>
  );
}
