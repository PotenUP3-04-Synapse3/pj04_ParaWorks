'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api';

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  risk_level: string | null;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    apiFetch<Project[]>('/projects').then(setProjects);
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">프로젝트</h1>
      <div className="grid gap-4">
        {projects.map((p) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="bg-white rounded-xl shadow px-6 py-4 hover:shadow-md transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900">{p.name}</p>
                {p.description && <p className="text-sm text-gray-500 mt-1">{p.description}</p>}
              </div>
              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full">
                {p.status}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
