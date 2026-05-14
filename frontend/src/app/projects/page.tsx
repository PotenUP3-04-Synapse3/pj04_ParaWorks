"use client";

import { BarChart3, CalendarDays, CheckCircle2, FolderKanban, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { ProjectMemory, ProjectsResponse } from "@/lib/api/types";

type Task = {
  id: string;
  title: string;
  owner: string;
  status: "대기" | "진행 중" | "검토" | "완료";
  start: number;
  span: number;
  date: string;
  evidenceReason: string;
  kind: "evidence" | "timeline";
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

const views = ["개요", "간트", "일정표", "보드", "목록"] as const;
type View = (typeof views)[number];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [view, setView] = useState<View>("간트");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    apiGet<ProjectsResponse>("/api/v1/projects")
      .then((response) => {
        if (!active) return;
        const mappedProjects = response.projects.map(projectFromMemory);
        setProjects(mappedProjects);
        setSelectedProjectId((current) => current || mappedProjects[0]?.id || "");
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "프로젝트 데이터를 불러오지 못했습니다.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0],
    [projects, selectedProjectId],
  );

  if (!selectedProject) {
    return (
      <div className="reference-dashboard space-y-4">
        <section className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Project Workspace</p>
            <h1>프로젝트</h1>
            <p>{loading ? "프로젝트 evidence를 불러오고 있습니다." : error || "승인된 프로젝트 evidence가 아직 없습니다."}</p>
          </div>
          <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
            <FolderKanban className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            0개 프로젝트
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Project Workspace</p>
          <h1>프로젝트</h1>
          <p>승인된 source evidence와 업무 기록을 프로젝트별 워크플로우로 확인합니다.</p>
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
            <p className="text-[12px] font-bold text-muted">담당 source {selectedProject.owner}</p>
            <h2 className="mt-1 text-[22px] font-extrabold leading-8 text-ink">{selectedProject.name}</h2>
            <p className="mt-2 max-w-3xl text-[13px] leading-6 text-muted">{selectedProject.summary}</p>
          </div>
          <span className={`priority-badge ${selectedProject.risk === "높음" ? "danger" : selectedProject.risk === "보통" ? "warning" : "success"}`}>
            위험도 {selectedProject.risk}
          </span>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <ProjectMetric icon={BarChart3} label="진행률" value={`${selectedProject.progress}%`} />
          <ProjectMetric icon={CalendarDays} label="최근 업데이트" value={selectedProject.due} />
          <ProjectMetric icon={Users} label="담당 source" value={selectedProject.owner} />
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

function projectFromMemory(memory: ProjectMemory): Project {
  const evidenceTasks = memory.evidence.map((evidence, index) => ({
    id: evidence.id || `${memory.project_key}:${evidence.source_id}:${index}`,
    title: cleanTaskTitle(evidence.title || evidence.task_summary || evidence.source_snippet, evidence.source_type),
    owner: sourceTypeLabel(evidence.source_type),
    status: taskStatus(evidence.source_type),
    start: Math.min(index + 1, 9),
    span: Math.min(Math.max(2, Math.ceil((evidence.source_snippet.length || 80) / 80)), 4),
    date: formatShortDate(evidence.timestamp),
    evidenceReason: evidence.evidence_reason,
    kind: "evidence" as const,
  }));
  const timelineTasks = memory.timeline_items.map((item, index) => ({
    id: item.id,
    title: cleanTaskTitle(item.title || item.summary || item.source_snippets[0] || "", item.item_type),
    owner: timelineTypeLabel(item.item_type),
    status: "완료" as const,
    start: Math.min(evidenceTasks.length + index + 1, 9),
    span: Math.min(Math.max(2, Math.ceil((item.summary.length || 80) / 80)), 4),
    date: formatShortDate(item.created_at),
    evidenceReason: item.evidence_reason,
    kind: "timeline" as const,
  }));
  const tasks = [...timelineTasks, ...evidenceTasks];
  return {
    id: memory.project_key,
    name: memory.name,
    owner: memory.source_types.map(sourceTypeLabel).join(", ") || "Approved memory",
    status: `${memory.evidence_count.toLocaleString()}개 evidence, ${memory.timeline_items.length.toLocaleString()}개 승인 업무`,
    due: formatShortDate(memory.latest_timestamp),
    progress: Math.min(90, 30 + tasks.length * 12),
    risk: memory.permission_level === "restricted" ? "높음" : memory.evidence_count >= 3 ? "보통" : "낮음",
    reviewCount: memory.pending_review_count,
    summary: memory.summary,
    tasks,
  };
}

function cleanTaskTitle(value: string, sourceType: string) {
  const title = value.trim();
  if (!title) return `${sourceTypeLabel(sourceType)} evidence`;
  if (/^slack (message|thread reply) in /i.test(title)) return "Slack 업무 evidence";
  return title.length > 120 ? `${title.slice(0, 117)}...` : title;
}

function taskStatus(sourceType: string): Task["status"] {
  if (sourceType === "drive") return "검토";
  if (sourceType === "slack") return "진행 중";
  return "대기";
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === "gmail") return "Gmail";
  if (sourceType === "gmail_attachment") return "Gmail 첨부";
  if (sourceType === "drive") return "Drive";
  if (sourceType === "calendar") return "Calendar";
  if (sourceType === "slack") return "Slack";
  return sourceType;
}

function timelineTypeLabel(itemType: string) {
  if (itemType === "decision_record") return "승인된 결정";
  if (itemType === "history_event") return "승인된 히스토리";
  if (itemType === "timeline_event") return "승인된 타임라인";
  if (itemType === "todo") return "승인된 할 일";
  return "승인된 업무";
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "날짜 없음";
  return new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit" }).format(date);
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
            <TaskRow key={task.id} task={task} />
          ))}
        </div>
      </div>
      <div className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
        <h3 className="text-[14px] font-extrabold text-ink">프로젝트 운영 기준</h3>
        <p className="mt-3 text-[13px] leading-6 text-muted">
          승인된 업무 기록과 source evidence를 함께 보여주되, trusted knowledge 승격은 Review Queue 승인 상태를 기준으로 유지합니다.
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
        <div key={task.id} className="grid grid-cols-[160px_repeat(10,minmax(32px,1fr))] items-center gap-2">
          <div className="min-w-0">
            <p className="truncate text-[13px] font-extrabold text-ink">{task.title}</p>
            <p className="text-[11px] text-muted">{task.owner}</p>
          </div>
          <div
            className={`h-8 rounded-md ${task.kind === "timeline" ? "bg-emerald-500" : "bg-[var(--primary)]"}`}
            style={{ gridColumn: `${task.start + 1} / span ${task.span}` }}
            title={`${task.title} - ${task.status}`}
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
        <article key={task.id} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
          <p className="text-[12px] font-extrabold text-[var(--primary-dark)]">{task.date}</p>
          <h3 className="mt-2 text-[14px] font-extrabold text-ink">{task.title}</h3>
          <p className="mt-2 text-[12px] text-muted">{task.owner} - {task.status}</p>
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
              <TaskCard key={task.id} task={task} />
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
        <span>담당</span>
        <span>상태</span>
        <span>날짜</span>
      </div>
      {tasks.map((task) => (
        <div key={task.id} className="grid grid-cols-[1fr_120px_100px_80px] gap-3 border-b border-line px-4 py-3 text-[13px] last:border-b-0">
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
      <span className="text-muted">{task.owner} - {task.status}</span>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  return (
    <article className="rounded-md border border-line bg-white p-3">
      <p className="text-[13px] font-extrabold text-ink">{task.title}</p>
      <p className="mt-2 text-[12px] text-muted">{task.owner} - {task.date}</p>
    </article>
  );
}
