"use client";

import {
  ArrowRight,
  Bell,
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FileText,
  FolderKanban,
  Inbox,
  LayoutDashboard,
  Link2,
  MessageCircle,
  Settings,
  Sparkles,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import { REVIEW_QUEUE_UPDATED_EVENT } from "@/lib/reviewQueueEvents";
import type { DashboardResponse } from "@/lib/api/types";

type TodayTask = {
  id: number;
  title: string;
  category: string;
  assignee: string;
  due_date: string;
  priority?: string;
};

type CalendarEventItem = {
  id: number;
  dateKey: string;
  time: string;
  title: string;
  source: string;
};

type CalendarDay = {
  key: string;
  day: number;
  date: Date;
  inMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isWeekend: boolean;
  events: CalendarEventItem[];
};

type ReviewListItem = readonly [id: number, title: string, source: string, due: string, priority: string, href: string];

const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [completedTaskIds, setCompletedTaskIds] = useState<Set<number>>(() => new Set());
  const [completingTaskIds, setCompletingTaskIds] = useState<Set<number>>(() => new Set());
  const [selectedDate, setSelectedDate] = useState(() => dateKey(new Date()));
  const [visibleMonth, setVisibleMonth] = useState(() => firstDayOfMonth(new Date()));
  const [calendarSelectionTouched, setCalendarSelectionTouched] = useState(false);
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const loadDashboard = useCallback(async () => {
    let active = true;
    setLoading(true);
    await apiGet<DashboardResponse>("/api/v1/dashboard")
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

  useEffect(() => {
    let active = true;
    void loadDashboard();
    const refreshDashboard = () => {
      if (active) void loadDashboard();
    };
    window.addEventListener(REVIEW_QUEUE_UPDATED_EVENT, refreshDashboard);
    return () => {
      active = false;
      window.removeEventListener(REVIEW_QUEUE_UPDATED_EVENT, refreshDashboard);
    };
  }, [loadDashboard]);

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

  const calendarEvents = useMemo(() => {
    const events = new Map<string, CalendarEventItem[]>();
    for (const event of dashboard?.calendar_events ?? dashboard?.today_events ?? []) {
      const key = dateKey(new Date(event.start));
      const row: CalendarEventItem = {
        id: event.id,
        dateKey: key,
        time: formatEventTime(event.start),
        title: event.title,
        source: event.attendee_summary || event.organizer || event.location || "Google Calendar",
      };
      events.set(key, [...(events.get(key) ?? []), row]);
    }
    return events;
  }, [dashboard?.calendar_events, dashboard?.today_events]);

  const selectedDateEvents = calendarEvents.get(selectedDate) ?? [];
  const visibleAssignedProjects = dashboard?.assigned_projects ?? [];
  const highPriorityCount = visibleTodayTasks.filter((task) => priorityTone(task.priority) === "danger").length;
  const visibleReviewItems: ReviewListItem[] =
    dashboard?.pending_items?.map((item) => [
      item.id,
      item.title,
      item.item_type,
      "기한 없음",
      item.confidence_score > 0.8 ? "높음" : "보통",
      item.review_url ?? `/review?itemId=${item.id}`,
    ]) ?? [];

  const calendarDays = useMemo(
    () => buildCalendarDays(visibleMonth, selectedDate, calendarEvents),
    [calendarEvents, selectedDate, visibleMonth],
  );

  useEffect(() => {
    if (calendarSelectionTouched || calendarEvents.size === 0 || calendarEvents.has(selectedDate)) {
      return;
    }
    const [firstEventDate] = Array.from(calendarEvents.keys()).sort();
    if (firstEventDate) {
      setSelectedDate(firstEventDate);
      setVisibleMonth(firstDayOfMonth(new Date(`${firstEventDate}T00:00:00+09:00`)));
    }
  }, [calendarEvents, calendarSelectionTouched, selectedDate]);

  async function completeTask(taskId: number) {
    setCompletingTaskIds((current) => new Set(current).add(taskId));
    try {
      await apiPost(`/api/v1/todos/${taskId}/complete`);
      setCompletedTaskIds((current) => new Set(current).add(taskId));
      setDashboard((current) =>
        current
          ? {
              ...current,
              today_todos: current.today_todos.filter((todo) => todo.id !== taskId),
            }
          : current,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "할 일을 완료 처리하지 못했습니다.");
    } finally {
      setCompletingTaskIds((current) => {
        const next = new Set(current);
        next.delete(taskId);
        return next;
      });
    }
  }

  function moveMonth(delta: number) {
    setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  return (
    <div className="dashboard-redesign">
      <section className="dashboard-topline">
        <div>
          <p>My Work Home</p>
          <h1>오늘의 업무 흐름</h1>
          <span>오늘 내가 처리해야 할 업무, 일정, 멘션, 담당 프로젝트를 한곳에서 확인합니다.</span>
        </div>
        <div className="dashboard-date-card">
          <CalendarDays className="h-4 w-4" aria-hidden="true" />
          <span>{syncDateStr}</span>
        </div>
      </section>

      {error ? <div className="dashboard-error">{error}</div> : null}

      <section className="dashboard-content-grid">
        <main className="dashboard-main-column">
          <HeroCard />

          <section className="dashboard-kpi-grid" aria-label="오늘의 핵심 지표">
            <KpiCard icon={CheckCircle2} label="오늘 할 일" value={`${visibleTodayTasks.length}건`} detail={`높은 우선순위 ${highPriorityCount}건`} />
            <KpiCard icon={Inbox} label="내 검토 대기" value={`${pendingReviewCount}건`} detail="검토사항" tone="purple" />
            <KpiCard icon={CalendarDays} label="오늘 일정" value={`${(dashboard?.today_events ?? []).length}개`} detail="연동 후 표시" tone="blue" />
            <KpiCard icon={FolderKanban} label="담당 프로젝트" value={`${visibleAssignedProjects.length}개`} detail="등록 프로젝트" tone="violet" />
          </section>

          <section className="dashboard-card" id="dashboard-tasks">
            <div className="dashboard-card-header">
              <SectionTitle title="오늘 해야 할 업무" count={`${visibleTodayTasks.length}`} />
              <Link href="/projects" className="dashboard-link">
                프로젝트 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="dashboard-task-list">
              {loading ? (
                <EmptyState text="오늘 할 일을 불러오는 중입니다." />
              ) : visibleTodayTasks.length > 0 ? (
                visibleTodayTasks.map((task) => (
                  <article key={task.id} className="dashboard-task-row">
                    <div className="min-w-0">
                      <h2>{task.title}</h2>
                      <p>
                        {task.category} · 담당: {task.assignee}
                      </p>
                    </div>
                    <div className="dashboard-task-meta">
                      <span className={`dashboard-priority ${priorityTone(task.priority)}`}>{priorityLabel(task.priority)}</span>
                      <span className="dashboard-time">
                        <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                        {task.due_date}까지
                      </span>
                      <button
                        type="button"
                        aria-label={`완료 ${task.title}`}
                        onClick={() => completeTask(task.id)}
                        disabled={completingTaskIds.has(task.id)}
                        className="dashboard-complete-button"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        {completingTaskIds.has(task.id) ? "처리 중" : "완료"}
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <EmptyState text="오늘 처리할 승인된 할 일이 없습니다." />
              )}
            </div>
          </section>

          <section className="dashboard-card" data-testid="dashboard-review-card">
            <div className="dashboard-card-header">
              <SectionTitle title="검토사항" count={`${pendingReviewCount}`} countTestId="dashboard-review-count" />
              <Link href="/review" className="dashboard-link">
                전체 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="dashboard-review-table">
              {visibleReviewItems.map(([id, title, source, due, priority, href]) => (
                <Link href={href} key={id} data-testid={`dashboard-review-link-${id}`} className="dashboard-review-row">
                  <span className="dashboard-review-title">{title}</span>
                  <span className="dashboard-source-badge">{source}</span>
                  <span className="dashboard-review-muted">{due}</span>
                  <span className={`dashboard-priority ${priority === "높음" ? "danger" : "warning"}`}>{priority}</span>
                </Link>
              ))}
              {!loading && visibleReviewItems.length === 0 ? <EmptyState text="검토 대기 항목이 없습니다." /> : null}
            </div>
          </section>

          <section className="dashboard-card">
            <div className="dashboard-card-header">
              <SectionTitle title="담당 프로젝트" count={`${visibleAssignedProjects.length}`} />
              <Link href="/timeline" className="dashboard-link">
                타임라인 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="dashboard-project-grid">
              {visibleAssignedProjects.map((project) => (
                <article key={project.project_key} className="dashboard-project-card">
                  <span>
                    <FolderKanban className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <h2>{project.name}</h2>
                  <p>{project.summary}</p>
                  <strong>
                    근거 {project.evidence_count.toLocaleString()}건 · 활동 {project.activity_count.toLocaleString()}건 · 검토 대기{" "}
                    {project.pending_review_count.toLocaleString()}건
                  </strong>
                </article>
              ))}
              {!loading && visibleAssignedProjects.length === 0 ? <EmptyState text="등록된 담당 프로젝트가 없습니다." /> : null}
            </div>
          </section>
        </main>

        <aside className="dashboard-utility-column">
          <section className="dashboard-calendar-card" data-testid="dashboard-calendar">
            <div className="dashboard-calendar-header">
              <div>
                <p>오늘 일정</p>
                <h2>{visibleMonth.getFullYear()}년 {visibleMonth.getMonth() + 1}월</h2>
              </div>
              <div className="dashboard-calendar-controls">
                <button type="button" aria-label="이전 월" onClick={() => moveMonth(-1)}>
                  <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                </button>
                <button type="button" aria-label="다음 월" onClick={() => moveMonth(1)}>
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </div>

            <div className="dashboard-calendar-weekdays">
              {WEEKDAY_LABELS.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>

            <div className="dashboard-calendar-grid">
              {calendarDays.map((day) => (
                <div
                  key={day.key}
                  className="dashboard-calendar-day-shell"
                  onMouseEnter={() => setHoveredDate(day.key)}
                  onMouseLeave={() => setHoveredDate(null)}
                >
                  <button
                    type="button"
                    data-testid={`calendar-day-${day.key}`}
                    className={[
                      "dashboard-calendar-day",
                      day.inMonth ? "" : "outside",
                      day.isWeekend ? "weekend" : "",
                      day.isToday ? "today" : "",
                      day.isSelected ? "selected" : "",
                    ].join(" ")}
                    onClick={() => {
                      setCalendarSelectionTouched(true);
                      setSelectedDate(day.key);
                    }}
                  >
                    <span>{day.day}</span>
                    {day.events.length ? <i aria-hidden="true" /> : null}
                  </button>
                  {hoveredDate === day.key ? (
                    <div className="dashboard-calendar-popover">
                      <strong>{formatKoreanDate(day.date)}</strong>
                      {day.events.length ? (
                        day.events.map((event) => (
                          <p key={event.id}>
                            {event.time} {event.title}
                          </p>
                        ))
                      ) : (
                        <p>일정 없음</p>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>

            <div className="dashboard-selected-events">
              <div className="dashboard-selected-events-header">
                <h3>{formatKoreanDate(new Date(`${selectedDate}T00:00:00+09:00`))}</h3>
                <span>{selectedDateEvents.length}개 일정</span>
              </div>
              <div className="dashboard-event-list">
                {selectedDateEvents.length ? (
                  selectedDateEvents.map((event) => (
                    <article key={event.id} className="dashboard-event-row">
                      <time>{event.time}</time>
                      <div>
                        <h4>{event.title}</h4>
                        <p>{event.source}</p>
                      </div>
                    </article>
                  ))
                ) : (
                  <EmptyState text="일정 없음" compact />
                )}
              </div>
            </div>
          </section>

          <section className="dashboard-ai-card">
            <span className="dashboard-ai-icon">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </span>
            <h2>오늘의 AI 비서 제안</h2>
            <p>
              검토사항 {pendingReviewCount.toLocaleString()}건 중 높은 우선순위 항목을 먼저 처리해보세요. 오늘 일정과 충돌하는 업무는 AI에게 정리 요청할 수 있습니다.
            </p>
            <Link href="/search" className="dashboard-ai-button">
              AI에게 정리 요청
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </section>

          <section className="dashboard-quick-card">
            <h2>빠른 이동</h2>
            <div>
              <QuickLink href="/search" icon={Bot} label="AI 비서" />
              <QuickLink href="/agent-runs" icon={LayoutDashboard} label="에이전트 실행 기록" />
              <QuickLink href="/integrations" icon={Link2} label="연동 관리" />
              <QuickLink href="/notifications" icon={Bell} label="알림" />
              <QuickLink href="/admin" icon={Settings} label="관리자 콘솔" />
            </div>
          </section>
        </aside>
      </section>
    </div>
  );
}

function HeroCard() {
  return (
    <section className="dashboard-hero">
      <div className="dashboard-hero-copy">
        <p>AI WORKSPACE</p>
        <h2>오늘도 좋은 흐름으로 시작해볼까요?</h2>
        <span>처리할 업무와 검토사항, 일정을 한눈에 확인하고 우선순위를 정리하세요.</span>
        <a href="#dashboard-tasks" className="dashboard-hero-button">
          오늘 업무 확인하기
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </a>
      </div>
      <HeroIllustration />
    </section>
  );
}

function HeroIllustration() {
  return (
    <div className="dashboard-hero-illustration" aria-hidden="true">
      <div className="hero-orbit one" />
      <div className="hero-orbit two" />
      <div className="hero-workspace-panel">
        <div className="hero-panel-top">
          <div className="hero-avatar-cluster">
            <span />
            <span />
            <span />
          </div>
          <div className="hero-window-actions">
            <i />
            <i />
            <i />
          </div>
        </div>
        <div className="hero-chat-row">
          <span className="hero-icon-bubble">
            <MessageCircle className="h-4 w-4" />
          </span>
          <div>
            <i className="wide" />
            <i />
          </div>
        </div>
        <div className="hero-card-stack">
          <span>
            <CheckCircle2 className="h-4 w-4" />
            검토 완료
          </span>
          <span>
            <FileText className="h-4 w-4" />
            회의록 요약
          </span>
          <span>
            <UsersRound className="h-4 w-4" />
            팀 공유
          </span>
        </div>
      </div>
      <div className="hero-floating-card hero-floating-check">
        <CheckCircle2 className="h-6 w-6" />
      </div>
      <div className="hero-floating-card hero-floating-bot">
        <Bot className="h-7 w-7" />
      </div>
      <div className="hero-floating-card hero-floating-doc">
        <FileText className="h-6 w-6" />
      </div>
    </div>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = "blue",
}: {
  icon: typeof CheckCircle2;
  label: string;
  value: string;
  detail: string;
  tone?: "blue" | "purple" | "violet";
}) {
  return (
    <article className={`dashboard-kpi-card ${tone}`}>
      <span>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </article>
  );
}

function SectionTitle({ title, count, countTestId }: { title: string; count?: string; countTestId?: string }) {
  return (
    <div className="dashboard-section-title">
      <h2>{title}</h2>
      {count ? <span data-testid={countTestId}>{count}</span> : null}
    </div>
  );
}

function QuickLink({ href, icon: Icon, label }: { href: string; icon: typeof Bot; label: string }) {
  return (
    <Link href={href} className="dashboard-quick-link">
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{label}</span>
      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
    </Link>
  );
}

function EmptyState({ text, compact = false }: { text: string; compact?: boolean }) {
  return <p className={`dashboard-empty ${compact ? "compact" : ""}`}>{text}</p>;
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

function formatEventTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul",
  });
}

function firstDayOfMonth(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), 1);
}

function dateKey(value: Date) {
  return value.toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });
}

function buildCalendarDays(month: Date, selectedDate: string, events: Map<string, CalendarEventItem[]>): CalendarDay[] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const start = new Date(first);
  start.setDate(first.getDate() - first.getDay());
  const today = dateKey(new Date());

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const key = dateKey(date);
    return {
      key,
      day: date.getDate(),
      date,
      inMonth: date.getMonth() === month.getMonth(),
      isToday: key === today,
      isSelected: key === selectedDate,
      isWeekend: date.getDay() === 0 || date.getDay() === 6,
      events: events.get(key) ?? [],
    };
  });
}

function formatKoreanDate(value: Date) {
  return value.toLocaleDateString("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "short",
    timeZone: "Asia/Seoul",
  });
}
