import { ArrowRight, Bell, CheckCircle2, Clock3, FileText, MessageSquare, Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { serverApiGet } from "@/lib/api/server";
import type { DashboardResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const todayTasks = [
  {
    title: "ORION 요구사항 변경안 검토",
    project: "프로젝트 ORION",
    due: "오늘 14:00",
    priority: "높음",
    status: "검토 필요",
    source: "Slack #project-orion",
  },
  {
    title: "Oracle DB 선정 근거 확인",
    project: "프로젝트 ORION",
    due: "오늘 16:00",
    priority: "높음",
    status: "진행 중",
    source: "Gmail 스레드",
  },
  {
    title: "보안 정책 초안 코멘트",
    project: "Nova 보안 정책",
    due: "오늘 17:30",
    priority: "보통",
    status: "대기",
    source: "Drive 정책 문서",
  },
];

const upcomingEvents = [
  ["10:30", "ORION 요구사항 영향도 회의", "김하나 외 5명"],
  ["13:00", "보안 정책 리뷰", "박지은, 정민철"],
  ["16:30", "Atlas API 배포 체크", "이준호"],
];

const assignedProjects = [
  ["프로젝트 ORION", "68%", "요구사항 변경 검토", "높음"],
  ["Nova 보안 정책", "54%", "정책 초안 리뷰", "보통"],
  ["Atlas API 개선", "76%", "성능 개선 실행", "낮음"],
];

const personalUpdates = [
  {
    icon: MessageSquare,
    title: "김하나님이 #project-orion에서 멘션했습니다.",
    detail: "권한 분리 요구사항 영향도 확인 요청",
    time: "8분 전",
  },
  {
    icon: FileText,
    title: "ORION_PRD_v2.docx가 수정되었습니다.",
    detail: "내 검토 항목과 연결된 문서 변경",
    time: "21분 전",
  },
  {
    icon: Bell,
    title: "검토사항에 새 후보 2건이 배정되었습니다.",
    detail: "제한 권한 근거 포함, 오늘 처리 권장",
    time: "35분 전",
  },
];

const reviewItems = [
  ["ORION 요구사항 변경 검토", "Slack", "오늘 14:00", "높음"],
  ["Oracle DB 선정 근거 확인", "Gmail", "오늘 16:00", "높음"],
  ["보안 정책 초안 코멘트", "Drive", "내일 10:00", "보통"],
];

export default async function DashboardPage() {
  const dashboard = await serverApiGet<DashboardResponse>("/api/v1/dashboard").catch(() => null);
  const pendingReviewCount = dashboard?.pending_review_count ?? 0;
  const visibleTodayTasks: typeof todayTasks = [];
  const visibleUpcomingEvents: typeof upcomingEvents = [];
  const visibleAssignedProjects: typeof assignedProjects = [];
  const visiblePersonalUpdates: typeof personalUpdates = [];
  const visibleReviewItems: typeof reviewItems = [];

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
          2026.05.11 월요일
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
              <PanelTitle title="오늘 해야 할 업무" count={`${visibleTodayTasks.length}건`} />
              <Link href="/projects" className="text-link">
                프로젝트 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-3 space-y-3">
              {visibleTodayTasks.map((task) => (
                <article key={task.title} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-[15px] font-extrabold text-ink">{task.title}</h2>
                      <p className="mt-1 text-[12px] font-bold text-muted">{task.project} · {task.source}</p>
                    </div>
                    <span className={`priority-badge ${task.priority === "높음" ? "danger" : "warning"}`}>
                      {task.priority}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] font-bold text-muted">
                    <span className="badge blue">{task.status}</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                      {task.due}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="검토사항" count={`${visibleReviewItems.length}건`} />
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
