'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

interface Todo {
  id: string;
  title: string;
  assignee: string | null;
  due_date: string | null;
  priority: string | null;
  priority_score: number | null;
  status: string;
  confidence_score: number | null;
  source_links: string[] | null;
}

interface TimelineEvent {
  id: string;
  title: string;
  result_summary: string | null;
  event_time: string | null;
  status: string;
  source_links: string[] | null;
}

interface HistoryEvent {
  id: string;
  title: string;
  situation: string | null;
  decision: string | null;
  decision_maker: string | null;
  event_time: string | null;
  status: string;
  source_links: string[] | null;
  source_snippets: Record<string, unknown>[] | null;
}

type Tab = 'todos' | 'timeline' | 'history';

export default function ProjectDetailPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const [tab, setTab] = useState<Tab>('todos');
  const [todos, setTodos] = useState<Todo[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [hoveredHistory, setHoveredHistory] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Todo[]>(`/projects/${projectId}/todos`).then(setTodos);
    apiFetch<TimelineEvent[]>(`/projects/${projectId}/timeline`).then(setTimeline);
    apiFetch<HistoryEvent[]>(`/projects/${projectId}/history`).then(setHistory);
  }, [projectId]);

  return (
    <div className="p-8 space-y-6">
      {/* Tab bar */}
      <div className="flex gap-4 border-b">
        {(['todos', 'timeline', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500'
            }`}
          >
            {t === 'todos' ? '할 일' : t === 'timeline' ? '타임라인' : '의사결정 히스토리'}
          </button>
        ))}
      </div>

      {/* Todos */}
      {tab === 'todos' && (
        <div className="space-y-3">
          {todos.map((todo) => (
            <div key={todo.id} className="bg-white rounded-xl shadow px-5 py-4">
              <div className="flex justify-between items-start">
                <p className="font-medium">{todo.title}</p>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  todo.priority === 'critical' ? 'bg-red-100 text-red-700' :
                  todo.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {todo.priority || 'medium'}
                </span>
              </div>
              <div className="text-sm text-gray-500 mt-1 flex gap-4">
                {todo.assignee && <span>담당: {todo.assignee}</span>}
                {todo.due_date && <span>마감: {todo.due_date}</span>}
                <span className="ml-auto">신뢰도: {((todo.confidence_score || 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Timeline */}
      {tab === 'timeline' && (
        <div className="relative border-l-2 border-indigo-200 pl-6 space-y-6">
          {timeline.map((ev) => (
            <div key={ev.id} className="relative">
              <div className="absolute -left-8 top-1 w-4 h-4 rounded-full bg-indigo-500" />
              <div className="bg-white rounded-xl shadow px-5 py-4">
                <p className="font-medium">{ev.title}</p>
                {ev.result_summary && <p className="text-sm text-gray-600 mt-1">{ev.result_summary}</p>}
                <p className="text-xs text-gray-400 mt-2">{ev.event_time?.slice(0, 10)}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* History */}
      {tab === 'history' && (
        <div className="space-y-3">
          {history.map((h) => (
            <div
              key={h.id}
              className="bg-white rounded-xl shadow px-5 py-4 relative"
              onMouseEnter={() => setHoveredHistory(h.id)}
              onMouseLeave={() => setHoveredHistory(null)}
            >
              <p className="font-medium">{h.title}</p>
              {h.decision && <p className="text-sm text-gray-700 mt-1">결정: {h.decision}</p>}
              {h.decision_maker && <p className="text-xs text-gray-500">결정자: {h.decision_maker}</p>}

              {/* Source snippets popup on hover */}
              {hoveredHistory === h.id && h.source_snippets && h.source_snippets.length > 0 && (
                <div className="absolute z-10 left-0 top-full mt-2 w-full bg-white border border-gray-200 rounded-xl shadow-xl p-4 text-xs text-gray-600 space-y-2">
                  <p className="font-semibold text-gray-700">근거 출처</p>
                  {h.source_snippets.slice(0, 3).map((s, i) => (
                    <p key={i} className="line-clamp-2">{String(s)}</p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
