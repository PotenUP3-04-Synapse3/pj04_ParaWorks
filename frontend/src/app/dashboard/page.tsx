'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

interface Stats {
  total_projects: number;
  active_projects: number;
  pending_reviews: number;
  total_approved_todos: number;
}

interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  risk_level: string | null;
  todo_count: number;
}

interface DashboardData {
  stats: Stats;
  recent_projects: ProjectSummary[];
}

const riskColor = (risk: string | null) => {
  if (risk === 'high') return 'text-red-600';
  if (risk === 'medium') return 'text-yellow-600';
  return 'text-green-600';
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch<DashboardData>('/dashboard')
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-500">{error}</p>;
  if (!data) return <p className="text-gray-500">로딩 중...</p>;

  const { stats, recent_projects } = data;

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '전체 프로젝트', value: stats.total_projects },
          { label: '활성 프로젝트', value: stats.active_projects },
          { label: '검토 대기', value: stats.pending_reviews },
          { label: '승인된 할 일', value: stats.total_approved_todos },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
            <span className="text-sm text-gray-500">{s.label}</span>
            <span className="text-3xl font-bold text-gray-900">{s.value}</span>
          </div>
        ))}
      </div>

      {/* Recent projects */}
      <div>
        <h2 className="text-lg font-semibold mb-3">최근 프로젝트</h2>
        <div className="grid gap-3">
          {recent_projects.map((p) => (
            <a
              key={p.id}
              href={`/projects/${p.id}`}
              className="bg-white rounded-xl shadow px-5 py-4 flex items-center justify-between hover:shadow-md transition"
            >
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="text-sm text-gray-400">{p.status}</p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                {p.risk_level && (
                  <span className={riskColor(p.risk_level)}>Risk: {p.risk_level}</span>
                )}
                <span className="text-gray-500">{p.todo_count} todos</span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
