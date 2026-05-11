"use client";

import { BarChart3, CalendarDays, CheckCircle2, FolderKanban, Users } from "lucide-react";
import { useMemo, useState } from "react";

type Task = {
  title: string;
  owner: string;
  status: "대기" | "진행 중" | "검토" | "완료";
  start: number;
  span: number;
  date: string;
};

type Project = {
  id: string;
  name: string;
  owner: string;
  status: string;
  due: string;
  progress: number;
  risk: "낮음" | "보통" | "높음";
  reviewCount: number;
  summary: string;
  tasks: Task[];
};

const projects: Project[] = [
  {
    id: "orion",
    name: "프로젝트 ORION",
    owner: "김하나",
    status: "요구사항 변경 검토",
    due: "2026.05.22",
    progress: 68,
    risk: "높음",
    reviewCount: 7,
    summary: "고객사 요구사항 변경, DB 선정 근거, 공유본 작성을 같은 프로젝트 계획에서 관리합니다.",
    tasks: [
      { title: "요구사항 변경안 정리", owner: "김하나", status: "검토", start: 1, span: 3, date: "05.13" },
      { title: "Oracle DB 선정 근거 확정", owner: "이준호", status: "진행 중", start: 3, span: 4, date: "05.16" },
      { title: "고객사 공유본 작성", owner: "최유리", status: "대기", start: 6, span: 3, date: "05.20" },
      { title: "최종 승인 회의", owner: "박지은", status: "대기", start: 9, span: 2, date: "05.22" },
    ],
  },
  {
    id: "nova",
    name: "Nova 보안 정책",
    owner: "박지은",
    status: "정책 초안 리뷰",
    due: "2026.05.17",
    progress: 54,
    risk: "보통",
    reviewCount: 4,
    summary: "보안 점검 결과와 정책 초안을 일정표, 보드, 검토 항목으로 나누어 추적합니다.",
    tasks: [
      { title: "정책 초안 리뷰", owner: "박지은", status: "진행 중", start: 1, span: 2, date: "05.12" },
      { title: "권한 영향 범위 확인", owner: "정민철", status: "검토", start: 3, span: 2, date: "05.14" },
      { title: "운영팀 공지 작성", owner: "최유리", status: "대기", start: 5, span: 3, date: "05.16" },
    ],
  },
  {
    id: "atlas",
    name: "Atlas API 개선",
    owner: "이준호",
    status: "성능 개선 실행",
    due: "2026.05.29",
    progress: 76,
    risk: "낮음",
    reviewCount: 2,
    summary: "성능 병목, 캐시 정책, 릴리스 노트를 한 프로젝트 보드에서 확인합니다.",
    tasks: [
      { title: "병목 구간 정리", owner: "이준호", status: "완료", start: 1, span: 2, date: "05.12" },
      { title: "캐시 정책 적용", owner: "정민철", status: "진행 중", start: 3, span: 5, date: "05.20" },
      { title: "릴리스 노트 준비", owner: "김하나", status: "대기", start: 8, span: 2, date: "05.27" },
    ],
  },
];

const views = ["개요", "간트", "일정표", "보드", "목록"] as const;
type View = (typeof views)[number];

export default function ProjectsPage() {
  const [selectedProjectId, setSelectedProjectId] = useState(projects[0].id);
  const [view, setView] = useState<View>("간트");
  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0],
    [selectedProjectId],
  );

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Project Workspace</p>
          <h1>프로젝트</h1>
          <p>담당 프로젝트를 선택하고 간트 차트, 일정표, 보드, 목록으로 업무 흐름을 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <FolderKanban className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {projects.length.toLocaleString()}개 프로젝트
        </div>
      </section>

      <nav className="panel reference-panel flex gap-2 overflow-x-auto p-2" aria-label="프로젝트 선택">
        {projects.map((project) => (
          <button
            key={project.id}
            type="button"
            aria-pressed={project.id === selectedProjectId}
            className={`shrink-0 rounded-md px-3 py-2 text-left text-[13px] font-extrabold transition ${
              project.id === selectedProjectId
                ? "bg-[var(--primary)] text-white shadow-sm ring-2 ring-[var(--primary-soft)]"
                : "bg-[var(--glass-elevated)] text-ink hover:bg-[var(--glass-strong)]"
            }`}
            onClick={() => setSelectedProjectId(project.id)}
          >
            {project.name}
          </button>
        ))}
      </nav>

      <section className="panel reference-panel">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
          <div>
            <p className="text-[12px] font-bold text-muted">담당자 {selectedProject.owner}</p>
            <h2 className="mt-1 text-[22px] font-extrabold leading-8 text-ink">{selectedProject.name}</h2>
            <p className="mt-2 max-w-3xl text-[13px] leading-6 text-muted">{selectedProject.summary}</p>
          </div>
          <span className={`priority-badge ${selectedProject.risk === "높음" ? "danger" : selectedProject.risk === "보통" ? "warning" : "success"}`}>
            위험도 {selectedProject.risk}
          </span>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <ProjectMetric icon={BarChart3} label="진행률" value={`${selectedProject.progress}%`} />
          <ProjectMetric icon={CalendarDays} label="목표일" value={selectedProject.due} />
          <ProjectMetric icon={Users} label="담당자" value={selectedProject.owner} />
          <ProjectMetric icon={CheckCircle2} label="검토 대기" value={`${selectedProject.reviewCount}건`} />
        </div>

        <div className="mt-4 flex gap-2 overflow-x-auto border-b border-line pb-3" role="tablist" aria-label="프로젝트 보기">
          {views.map((nextView) => (
            <button
              key={nextView}
              type="button"
              aria-pressed={view === nextView}
              className={`shrink-0 rounded-md px-3 py-2 text-[13px] font-extrabold ${
                view === nextView
                  ? "bg-[var(--primary-soft)] text-[var(--primary-dark)] shadow-sm ring-1 ring-[var(--primary)]"
                  : "text-muted hover:bg-surface-soft"
              }`}
              onClick={() => setView(nextView)}
            >
              {nextView}
            </button>
          ))}
        </div>

        <div className="mt-5">
          {view === "개요" ? <Overview project={selectedProject} /> : null}
          {view === "간트" ? <GanttView tasks={selectedProject.tasks} /> : null}
          {view === "일정표" ? <CalendarView tasks={selectedProject.tasks} /> : null}
          {view === "보드" ? <BoardView tasks={selectedProject.tasks} /> : null}
          {view === "목록" ? <ListView tasks={selectedProject.tasks} /> : null}
        </div>
      </section>
    </div>
  );
}

function ProjectMetric({ icon: Icon, label, value }: { icon: typeof FolderKanban; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
      <Icon className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
      <p className="mt-3 text-[12px] font-bold text-muted">{label}</p>
      <strong className="mt-1 block text-[15px] text-ink">{value}</strong>
    </div>
  );
}

function Overview({ project }: { project: Project }) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="rounded-lg border border-line bg-surface-soft p-4">
        <div className="flex items-center justify-between text-[13px] font-extrabold">
          <span>{project.status}</span>
          <span>{project.progress}%</span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-white">
          <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${project.progress}%` }} />
        </div>
        <div className="mt-4 grid gap-2">
          {project.tasks.map((task) => (
            <TaskRow key={task.title} task={task} />
          ))}
        </div>
      </div>
      <div className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
        <h3 className="text-[14px] font-extrabold text-ink">프로젝트 운영 기준</h3>
        <p className="mt-3 text-[13px] leading-6 text-muted">
          간트 차트로 의존성과 기간을 보고, 일정표로 마감 충돌을 확인하며, 보드와 목록에서 실행 상태를 관리합니다.
        </p>
      </div>
    </div>
  );
}

function GanttView({ tasks }: { tasks: Task[] }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-[160px_repeat(10,minmax(32px,1fr))] gap-2 text-[11px] font-bold text-muted">
        <span>업무</span>
        {Array.from({ length: 10 }, (_, index) => (
          <span key={index}>D+{index + 1}</span>
        ))}
      </div>
      {tasks.map((task) => (
        <div key={task.title} className="grid grid-cols-[160px_repeat(10,minmax(32px,1fr))] items-center gap-2">
          <div className="min-w-0">
            <p className="truncate text-[13px] font-extrabold text-ink">{task.title}</p>
            <p className="text-[11px] text-muted">{task.owner}</p>
          </div>
          <div
            className="h-8 rounded-md bg-[var(--primary)]"
            style={{ gridColumn: `${task.start + 1} / span ${task.span}` }}
            title={`${task.title} · ${task.status}`}
          />
        </div>
      ))}
    </div>
  );
}

function CalendarView({ tasks }: { tasks: Task[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {tasks.map((task) => (
        <article key={task.title} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
          <p className="text-[12px] font-extrabold text-[var(--primary-dark)]">{task.date}</p>
          <h3 className="mt-2 text-[14px] font-extrabold text-ink">{task.title}</h3>
          <p className="mt-2 text-[12px] text-muted">{task.owner} · {task.status}</p>
        </article>
      ))}
    </div>
  );
}

function BoardView({ tasks }: { tasks: Task[] }) {
  const columns: Task["status"][] = ["대기", "진행 중", "검토", "완료"];
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {columns.map((column) => (
        <section key={column} className="rounded-lg border border-line bg-surface-soft p-3">
          <h3 className="text-[13px] font-extrabold text-ink">{column}</h3>
          <div className="mt-3 space-y-2">
            {tasks.filter((task) => task.status === column).map((task) => (
              <TaskCard key={task.title} task={task} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function ListView({ tasks }: { tasks: Task[] }) {
  return (
    <div className="rounded-lg border border-line">
      <div className="grid grid-cols-[1fr_120px_100px_80px] gap-3 border-b border-line bg-surface-soft px-4 py-3 text-[12px] font-extrabold text-muted">
        <span>업무</span>
        <span>담당자</span>
        <span>상태</span>
        <span>마감</span>
      </div>
      {tasks.map((task) => (
        <div key={task.title} className="grid grid-cols-[1fr_120px_100px_80px] gap-3 border-b border-line px-4 py-3 text-[13px] last:border-b-0">
          <span className="font-bold text-ink">{task.title}</span>
          <span className="text-muted">{task.owner}</span>
          <span className="text-muted">{task.status}</span>
          <span className="text-muted">{task.date}</span>
        </div>
      ))}
    </div>
  );
}

function TaskRow({ task }: { task: Task }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-[13px]">
      <span className="font-bold text-ink">{task.title}</span>
      <span className="text-muted">{task.owner} · {task.status}</span>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  return (
    <article className="rounded-md border border-line bg-white p-3">
      <p className="text-[13px] font-extrabold text-ink">{task.title}</p>
      <p className="mt-2 text-[12px] text-muted">{task.owner} · {task.date}</p>
    </article>
  );
}
