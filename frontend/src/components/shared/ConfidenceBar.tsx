interface ConfidenceBarProps {
  score: number; // 0~1
}

export function ConfidenceBar({ score }: ConfidenceBarProps) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-9 text-right">{pct}%</span>
    </div>
  );
}
