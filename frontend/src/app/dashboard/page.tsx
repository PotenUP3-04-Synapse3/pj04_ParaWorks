"use client";

import { ArrowRight, CheckCircle2, Clock3, Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { DashboardResponse } from "@/lib/api/types";

type TodayTask = {
  id: number;
  title: string;
  category: string;
  assignee: string;
  due_date: string;
  priority?: string;
};

type UpcomingEvent = readonly [time: string, title: string, people: string];
type PersonalUpdate = {
  id: string;
  icon: typeof Sparkles;
  title: string;
  detail: string;
  time: string;
};
type ReviewListItem = readonly [id: number, title: string, source: string, due: string, priority: string];

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [completedTaskIds, setCompletedTaskIds] = useState<Set<number>>(() => new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    apiGet<DashboardResponse>("/api/v1/dashboard")
      .then((response) => {
        if (active) setDashboard(response);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "대시보드를 불러오지 못했습니다.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const pendingReviewCount = dashboard?.pending_review_count ?? 0;
  const syncDateStr = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  const visibleTodayTasks: TodayTask[] = useMemo(
    () =>
      (dashboard?.today_todos ?? [])
        .filter((todo) => !completedTaskIds.has(todo.id))
        .map((todo) => ({
          id: todo.id,
          title: todo.title,
          category: todo.category,
          assignee: todo.assignee,
          due_date: todo.due_date,
          priority: todo.priority,
        })),
    [completedTaskIds, dashboard?.today_todos],
  );
  const visibleUpcomingEvents: UpcomingEvent[] = [];
  const visibleAssignedProjects = dashboard?.assigned_projects ?? [];
  const highPriorityCount = visibleTodayTasks.filter((task) => priorityTone(task.priority) === "danger").length;
  const visiblePersonalUpdates: PersonalUpdate[] = [
    ...(dashboard?.recent_decisions?.map((d) => ({
      id: `decision-${d.id}`,
      icon: Sparkles,
      title: `[의사결정] ${d.title}`,
      detail: d.summary,
      time: new Date(d.created_at).toLocaleDateString(),
    })) ?? []),
    ...(dashboard?.recent_timeline?.map((t) => ({
      id: `timeline-${t.id}`,
      icon: Clock3,
      title: `[타임라인] ${t.title}`,
      detail: `${t.summary} · 신뢰도 ${Math.round(t.confidence_score * 100)}%`,
      time: new Date(t.created_at).toLocaleDateString(),
    })) ?? []),
  ];
  const visibleReviewItems: ReviewListItem[] =
    dashboard?.pending_items?.map((item) => [
      item.id,
      item.title,
      item.item_type,
      "기한 없음",
      item.confidence_score > 0.8 ? "높음" : "보통",
    ]) ?? [];

  function completeTask(taskId: number) {
    setCompletedTaskIds((current) => new Set(current).add(taskId));
  }

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">My Work Home</p>
          <h1>오늘의 업무 흐름</h1>
          <p>오늘 내가 처리해야 할 업무, 일정, 멘션, 담당 프로젝트를 한곳에서 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Clock3 className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {syncDateStr}
        </div>
      </section>

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

      <section className="grid gap-3 md:grid-cols-4">
        <PersonalMetric label="오늘 할 일" value={`${visibleTodayTasks.length}건`} detail={`높은 우선순위 ${highPriorityCount}건`} />
        <PersonalMetric label="내 검토 대기" value={`${pendingReviewCount}건`} detail="검토사항" />
        <PersonalMetric label="오늘 일정" value={`${visibleUpcomingEvents.length}개`} detail="연동 후 표시" />
        <PersonalMetric label="담당 프로젝트" value={`${visibleAssignedProjects.length}개`} detail="등록 프로젝트" />
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="오늘 해야 할 업무" count={`${visibleTodayTasks.length}`} />
              <Link href="/projects" className="text-link">
                프로젝트 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-3 space-y-3">
              {loading ? (
                <EmptyState text="오늘 할 일을 불러오는 중입니다." />
              ) : visibleTodayTasks.length > 0 ? (
                visibleTodayTasks.map((task) => (
                  <article key={task.id} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="text-[15px] font-extrabold text-ink">{task.title}</h2>
                        <p className="mt-1 text-[12px] font-bold text-muted">
                          {task.category} · 담당: {task.assignee}
                        </p>
                      </div>
                      <span className={`priority-badge ${priorityTone(task.priority)}`}>
                        {priorityLabel(task.priority)}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[12px] font-bold text-muted">
                      <span className="inline-flex items-center gap-1">
                        <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                        {task.due_date}까지
                      </span>
                      <button
                        type="button"
                        aria-label={`완료 ${task.title}`}
                        onClick={() => completeTask(task.id)}
                        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-line bg-white px-3 text-[12px] font-extrabold text-ink hover:bg-surface-soft"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                        완료
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <EmptyState text="오늘 처리할 승인된 할 일이 없습니다." />
              )}
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="검토사항" count={`${visibleReviewItems.length}`} />
              <Link href="/review" className="text-link">
                전체 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-3 grid gap-2">
              {visibleReviewItems.map(([id, title, source, due, priority]) => (
                <div key={id} className="grid gap-2 rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[13px] sm:grid-cols-[1fr_84px_92px_58px] sm:items-center">
                  <span className="font-extrabold text-ink">{title}</span>
                  <span className="text-muted">{source}</span>
                  <span className="text-muted">{due}</span>
                  <span className={`priority-badge ${priority === "높음" ? "danger" : "warning"}`}>{priority}</span>
                </div>
              ))}
              {!loading && visibleReviewItems.length === 0 ? <EmptyState text="검토 대기 항목이 없습니다." /> : null}
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="내 담당 프로젝트" count={`${visibleAssignedProjects.length}`} />
              <Link href="/timeline" className="text-link">
                타임라인 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {visibleAssignedProjects.map((project) => (
                <article key={project.project_key} className="rounded-lg border border-line bg-surface-soft p-4">
                  <h2 className="text-[14px] font-extrabold text-ink">{project.name}</h2>
                  <p className="mt-2 line-clamp-2 text-[12px] font-bold leading-5 text-muted">{project.summary}</p>
                  <p className="mt-3 text-[12px] font-extrabold text-[var(--primary-dark)]">
                    근거 {project.evidence_count.toLocaleString()}건 · 활동 {project.activity_count.toLocaleString()}건 · 검토 대기 {project.pending_review_count.toLocaleString()}건
                  </p>
                </article>
              ))}
              {!loading && visibleAssignedProjects.length === 0 ? <EmptyState text="등록된 프로젝트가 없습니다." /> : null}
            </div>
          </Panel>
        </div>

        <aside className="space-y-4">
          <Panel>
            <PanelTitle title="오늘 일정" />
            <div className="mt-3 space-y-2">
              {visibleUpcomingEvents.map(([time, title, people]) => (
                <div key={`${time}-${title}`} className="flex gap-3 rounded-lg border border-line bg-surface-soft p-3">
                  <span className="w-12 shrink-0 text-[12px] font-extrabold text-[var(--primary-dark)]">{time}</span>
                  <div>
                    <p className="text-[13px] font-extrabold text-ink">{title}</p>
                    <p className="mt-1 text-[12px] text-muted">{people}</p>
                  </div>
                </div>
              ))}
              {!loading && visibleUpcomingEvents.length === 0 ? <EmptyState text="오늘 일정은 아직 연결되지 않았습니다." /> : null}
            </div>
          </Panel>

          <Panel>
            <PanelTitle title="내게 온 업데이트" />
            <div className="mt-3 space-y-3">
              {visiblePersonalUpdates.map((update) => {
                const Icon = update.icon;
                return (
                  <article key={update.id} className="flex gap-3 rounded-lg border border-line bg-[var(--glass-elevated)] p-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-[var(--primary-soft)] text-[var(--primary-dark)]">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <div>
                      <h2 className="text-[13px] font-extrabold text-ink">{update.title}</h2>
                      <p className="mt-1 text-[12px] leading-5 text-muted">{update.detail}</p>
                      <p className="mt-1 text-[11px] font-bold text-muted">{update.time}</p>
                    </div>
                  </article>
                );
              })}
              {!loading && visiblePersonalUpdates.length === 0 ? <EmptyState text="새 업데이트가 없습니다." /> : null}
            </div>
          </Panel>

          <Panel>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-1 h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
              <div>
                <h2 className="text-[14px] font-extrabold text-ink">오늘의 AI 비서 제안</h2>
                <p className="mt-2 text-[13px] leading-6 text-muted">
                  Slack 또는 Google을 연동하면 실제 업무 맥락 기반 질문 제안이 표시됩니다.
                </p>
                <Link href="/search" className="primary-action mt-4">
                  AI 비서로 이동
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </div>
          </Panel>
        </aside>
      </section>
    </div>
  );
}

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel reference-panel ${className}`}>{children}</section>;
}

function PanelTitle({ title, count }: { title: string; count?: string }) {
  return (
    <div className="reference-panel-title">
      <h2>{title}</h2>
      {count ? <span>{count}</span> : null}
    </div>
  );
}

function PersonalMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="panel reference-panel">
      <div className="flex items-center gap-2 text-[13px] font-bold text-muted">
        <CheckCircle2 className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
        {label}
      </div>
      <strong className="mt-3 block text-[24px] leading-8 text-ink">{value}</strong>
      <p className="mt-1 text-[12px] font-bold text-muted">{detail}</p>
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-lg border border-dashed border-line p-4 text-sm leading-6 text-muted">{text}</p>;
}

function priorityTone(priority?: string) {
  if (priority === "high" || priority === "높음") return "danger";
  if (priority === "low" || priority === "낮음") return "success";
  return "warning";
}

function priorityLabel(priority?: string) {
  if (priority === "high") return "높음";
  if (priority === "low") return "낮음";
  if (priority === "medium") return "보통";
  return priority || "보통";
}
