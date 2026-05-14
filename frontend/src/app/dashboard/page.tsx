import { ArrowRight, CheckCircle2, Clock3, Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { serverApiGet } from "@/lib/api/server";
import type { DashboardResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type TodayTask = {
  title: string;
  category: string;
  assignee: string;
  due_date: string;
  status: string;
};

type UpcomingEvent = readonly [time: string, title: string, people: string];
type AssignedProject = readonly [name: string, progress: string, status: string, risk: string];
type PersonalUpdate = {
  icon: typeof Sparkles;
  title: string;
  detail: string;
  time: string;
};
type ReviewListItem = readonly [title: string, source: string, due: string, priority: string];


export default async function DashboardPage() {
  const dashboard = await serverApiGet<DashboardResponse>("/api/v1/dashboard").catch(() => null);
  const pendingReviewCount = dashboard?.pending_review_count ?? 0;
  const syncDateStr = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  const visibleTodayTasks: TodayTask[] = dashboard?.today_todos?.map((todo) => ({
    title: todo.title,
    category: todo.category,
    assignee: todo.assignee,
    due_date: todo.due_date,
    status: "검토 필요"
  })) ?? [];
  const visibleUpcomingEvents: UpcomingEvent[] = [];
  const visibleAssignedProjects: AssignedProject[] = [];
  const visiblePersonalUpdates: PersonalUpdate[] = [
    ...(dashboard?.recent_decisions?.map((d) => ({
      icon: Sparkles,
      title: `[의사결정] ${d.title}`,
      detail: d.summary,
      time: new Date(d.created_at).toLocaleDateString(),
    })) ?? []),
    ...(dashboard?.recent_timeline?.map((t) => ({
      icon: Clock3,
      title: `[타임라인] ${t.title}`,
      detail: `${t.summary} · 신뢰도 ${Math.round(t.confidence_score * 100)}%`,
      time: new Date(t.created_at).toLocaleDateString(),
    })) ?? []),
  ];
  const visibleReviewItems: ReviewListItem[] = dashboard?.pending_items?.map((item) => [
    item.title,
    item.item_type,
    "기한 없음",
    item.confidence_score > 0.8 ? "높음" : "보통"
  ]) ?? [];

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">My Work Home</p>
          <h1>대시보드</h1>
          <p>오늘 내가 처리해야 할 업무, 일정, 멘션, 담당 프로젝트를 한곳에서 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Clock3 className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {syncDateStr}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <PersonalMetric label="오늘 할 일" value={`${visibleTodayTasks.length}건`} detail="높은 우선순위 0건" />
        <PersonalMetric label="내 검토 대기" value={`${pendingReviewCount}건`} detail="검토사항" />
        <PersonalMetric label="오늘 일정" value={`${visibleUpcomingEvents.length}개`} detail="연동 후 표시" />
        <PersonalMetric label="담당 프로젝트" value={`${visibleAssignedProjects.length}개`} detail="연동 후 표시" />
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
              {visibleTodayTasks.length > 0 ? visibleTodayTasks.map((task) => (
                <article key={task.title} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-[15px] font-extrabold text-ink">{task.title}</h2>
                      <p className="mt-1 text-[12px] font-bold text-muted">{task.category} · 담당: {task.assignee}</p>
                    </div>
                    <span className="priority-badge warning">
                      {task.category}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] font-bold text-muted">
                    <span className="badge blue">검토 필요</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                      {task.due_date}까지
                    </span>
                  </div>
                </article>
              )) : (
                <div className="p-12 text-center text-muted font-bold border-2 border-dashed rounded-xl">
                  추출된 할 일이 없습니다. 슬랙 동기화를 진행해 주세요.
                </div>
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
              {visibleReviewItems.map(([title, source, due, priority]) => (
                <div key={title} className="grid gap-2 rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[13px] sm:grid-cols-[1fr_84px_92px_58px] sm:items-center">
                  <span className="font-extrabold text-ink">{title}</span>
                  <span className="text-muted">{source}</span>
                  <span className="text-muted">{due}</span>
                  <span className={`priority-badge ${priority === "높음" ? "danger" : "warning"}`}>{priority}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="내 담당 프로젝트" />
              <Link href="/timeline" className="text-link">
                타임라인 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {visibleAssignedProjects.map(([name, progress, status, risk]) => (
                <article key={name} className="rounded-lg border border-line bg-surface-soft p-4">
                  <h2 className="text-[14px] font-extrabold text-ink">{name}</h2>
                  <p className="mt-2 text-[12px] font-bold text-muted">{status}</p>
                  <div className="mt-4 flex items-center justify-between text-[12px] font-extrabold">
                    <span>{progress}</span>
                    <span className={risk === "높음" ? "text-red-700" : risk === "보통" ? "text-amber-700" : "text-emerald-700"}>
                      위험도 {risk}
                    </span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-white">
                    <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: progress }} />
                  </div>
                </article>
              ))}
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
            </div>
          </Panel>

          <Panel>
            <PanelTitle title="내게 온 업데이트" />
            <div className="mt-3 space-y-3">
              {visiblePersonalUpdates.map((update) => {
                const Icon = update.icon;
                return (
                  <article key={update.title} className="flex gap-3 rounded-lg border border-line bg-[var(--glass-elevated)] p-3">
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
