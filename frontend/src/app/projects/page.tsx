"use client";

import {
  ArrowRight,
  Bot,
  CheckCircle2,
  ExternalLink,
  FolderKanban,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type { ProjectMemory, ProjectsResponse } from "@/lib/api/types";

type ProjectCreateResponse = {
  status: string;
  project: {
    project_key: string;
    name: string;
    summary: string;
  };
};

const SOURCE_FILTERS = ["전체", "Drive", "Gmail", "Slack", "Calendar"] as const;
type SourceFilter = (typeof SOURCE_FILTERS)[number];

function sourceLabel(sourceType: string) {
  return {
    slack: "Slack",
    gmail: "Gmail",
    gmail_attachment: "Gmail",
    drive: "Drive",
    calendar: "Calendar",
  }[sourceType] ?? sourceType;
}

function itemTypeLabel(itemType: string) {
  return {
    decision_record: "결정",
    history_event: "히스토리",
    timeline_event: "타임라인",
    todo: "할 일",
    project_assignment: "프로젝트 연결",
  }[itemType] ?? itemType.replaceAll("_", " ");
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectMemory[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("전체");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [isCreating, setIsCreating] = useState(false);
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [createError, setCreateError] = useState<string>();
  const [createPending, setCreatePending] = useState(false);

  async function loadProjects(nextSelectedKey?: string) {
    setLoading(true);
    setError(undefined);
    try {
      const response = await apiGet<ProjectsResponse>("/api/v1/projects");
      const nextProjects = response.projects || [];
      setProjects(nextProjects);
      const preferredKey = nextSelectedKey || selectedKey;
      if (preferredKey && nextProjects.some((project) => project.project_key === preferredKey)) {
        setSelectedKey(preferredKey);
      } else {
        setSelectedKey(preferredProjectKey(nextProjects));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "프로젝트 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createProject() {
    if (!name.trim() || !summary.trim()) {
      setCreateError("프로젝트명과 설명을 모두 입력해 주세요.");
      return;
    }

    setCreatePending(true);
    setCreateError(undefined);
    try {
      const response = await apiPost<ProjectCreateResponse>("/api/v1/projects/define", {
        name: name.trim(),
        summary: summary.trim(),
      });
      setName("");
      setSummary("");
      setIsCreating(false);
      await loadProjects(response.project.project_key);
    } catch (caught) {
      setCreateError(caught instanceof Error ? caught.message : "프로젝트를 생성하지 못했습니다.");
    } finally {
      setCreatePending(false);
    }
  }

  const filteredProjects = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return projects;
    return projects.filter((project) =>
      `${project.name} ${project.summary} ${project.project_key}`.toLowerCase().includes(needle),
    );
  }, [projects, query]);

  const selectedProject = projects.find((project) => project.project_key === selectedKey);
  const filteredEvidence = useMemo(() => {
    if (!selectedProject) return [];
    if (sourceFilter === "전체") return selectedProject.evidence;
    return selectedProject.evidence.filter((item) => sourceLabel(item.source_type) === sourceFilter);
  }, [selectedProject, sourceFilter]);

  return (
    <div data-testid="project-workspace" className="mx-auto w-full max-w-[1560px] px-4 pb-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-extrabold text-indigo-600">Project Workspace</p>
          <h1 className="mt-1 text-4xl font-black tracking-tight text-slate-950">프로젝트</h1>
          <p className="mt-3 max-w-3xl text-base font-medium leading-7 text-slate-500">
            사용자가 만든 프로젝트를 기준으로 Slack, Gmail, Drive, Calendar 근거와 승인된 활동을 모아봅니다.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={() => void loadProjects()} disabled={loading} className="inline-flex h-10 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-extrabold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
            새로고침
          </button>
          <button type="button" onClick={() => setIsCreating(true)} className="inline-flex h-10 items-center gap-2 rounded-2xl bg-indigo-600 px-4 text-sm font-extrabold text-white shadow-sm transition hover:bg-indigo-700">
            <Plus className="h-4 w-4" aria-hidden="true" />
            새 프로젝트
          </button>
        </div>
      </header>

      {error ? <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">{error}</div> : null}
      {isCreating ? (
        <ProjectCreateCard
          name={name}
          summary={summary}
          createError={createError}
          createPending={createPending}
          onChangeName={setName}
          onChangeSummary={setSummary}
          onCreate={() => void createProject()}
          onCancel={() => setIsCreating(false)}
        />
      ) : null}

      {selectedProject ? <ProjectOverviewHero project={selectedProject} /> : <ProjectEmptyOverview />}

      <section
        data-testid="project-workspace-grid"
        className="grid grid-cols-1 gap-6 xl:grid-cols-[300px_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(0,1fr)_420px]"
      >
        <ProjectListPanel
          projects={projects}
          filteredProjects={filteredProjects}
          selectedKey={selectedKey}
          query={query}
          loading={loading}
          onChangeQuery={setQuery}
          onSelect={setSelectedKey}
          onCreate={() => setIsCreating(true)}
        />

        <ProjectEvidencePanel evidence={filteredEvidence} sourceFilter={sourceFilter} onChangeSourceFilter={setSourceFilter} />

        <ProjectActivityPanel activityItems={selectedProject?.activity_items ?? []} />
      </section>
    </div>
  );
}

function ProjectCreateCard({
  name,
  summary,
  createError,
  createPending,
  onChangeName,
  onChangeSummary,
  onCreate,
  onCancel,
}: {
  name: string;
  summary: string;
  createError?: string;
  createPending: boolean;
  onChangeName: (value: string) => void;
  onChangeSummary: (value: string) => void;
  onCreate: () => void;
  onCancel: () => void;
}) {
  return (
    <section className="mb-6 rounded-3xl border border-white/70 bg-white p-5 shadow-sm">
      <div className="grid gap-3 md:grid-cols-[minmax(0,280px)_1fr_auto] md:items-end">
        <label className="text-sm font-extrabold text-slate-900">
          프로젝트명
          <input value={name} onChange={(event) => onChangeName(event.target.value)} placeholder="예: 고객 포털 개편" className="mt-1 h-11 w-full rounded-2xl border border-slate-200 bg-white px-3 text-sm font-semibold outline-none transition focus:border-indigo-500" />
        </label>
        <label className="text-sm font-extrabold text-slate-900">
          간단한 설명
          <input
            value={summary}
            onChange={(event) => onChangeSummary(event.target.value)}
            placeholder="프로젝트 목적과 주요 키워드를 적어 주세요."
            className="mt-1 h-11 w-full rounded-2xl border border-slate-200 bg-white px-3 text-sm font-semibold outline-none transition focus:border-indigo-500"
          />
        </label>
        <div className="flex gap-2">
          <button type="button" onClick={onCreate} disabled={createPending} className="inline-flex h-10 items-center gap-2 rounded-2xl bg-indigo-600 px-4 text-sm font-extrabold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60">
            생성
          </button>
          <button type="button" onClick={onCancel} className="inline-flex h-10 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-extrabold text-slate-700 shadow-sm transition hover:bg-slate-50">
            취소
          </button>
        </div>
      </div>
      {createError ? <p className="mt-3 text-sm font-semibold text-red-700">{createError}</p> : null}
    </section>
  );
}

function ProjectOverviewHero({ project }: { project: ProjectMemory }) {
  return (
    <section data-testid="project-overview-hero" className="mb-6 overflow-hidden rounded-3xl border border-white/70 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-wide text-indigo-600">{project.project_key}</p>
          <h2 className="mt-1 break-keep text-3xl font-black tracking-tight text-slate-950 max-sm:break-normal">{project.name}</h2>
          <p className="mt-3 max-w-3xl text-sm font-medium leading-6 text-slate-500">{project.summary}</p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:min-w-[330px]">
          <MetricCard label="근거" value={project.evidence_count} />
          <MetricCard label="활동" value={project.activity_items.length} />
          <MetricCard label="검토 대기" value={project.pending_review_count} />
        </div>
      </div>
    </section>
  );
}

function ProjectEmptyOverview() {
  return (
    <section data-testid="project-overview-hero" className="mb-6 rounded-3xl border border-dashed border-indigo-100 bg-white p-6 shadow-sm">
      <p className="text-xs font-black uppercase tracking-wide text-indigo-600">PROJECT WORKSPACE</p>
      <h2 className="mt-2 text-2xl font-black text-slate-950">프로젝트를 선택해 주세요</h2>
      <p className="mt-3 max-w-2xl text-sm font-medium leading-6 text-slate-500">
        프로젝트를 만들면 승인된 원본 근거와 활동 기록을 같은 화면에서 탐색할 수 있습니다.
      </p>
    </section>
  );
}

function ProjectListPanel({
  projects,
  filteredProjects,
  selectedKey,
  query,
  loading,
  onChangeQuery,
  onSelect,
  onCreate,
}: {
  projects: ProjectMemory[];
  filteredProjects: ProjectMemory[];
  selectedKey: string;
  query: string;
  loading: boolean;
  onChangeQuery: (value: string) => void;
  onSelect: (value: string) => void;
  onCreate: () => void;
}) {
  return (
    <aside data-testid="project-list-panel" className="h-fit rounded-3xl border border-white/70 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-black text-slate-950">프로젝트 목록</h3>
          <p className="mt-1 text-sm font-semibold text-slate-500">{projects.length.toLocaleString()}개 프로젝트</p>
        </div>
        <button type="button" onClick={onCreate} className="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-50 text-indigo-600 transition hover:bg-indigo-100" aria-label="새 프로젝트">
          <FolderKanban className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <label className="flex h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 text-sm">
        <Search className="h-4 w-4 text-slate-400" aria-hidden="true" />
        <input value={query} onChange={(event) => onChangeQuery(event.target.value)} placeholder="프로젝트 검색" className="min-w-0 flex-1 bg-transparent font-semibold outline-none" />
      </label>

      <div className="mt-4 max-h-[620px] space-y-2 overflow-y-auto pr-1">
        {loading ? <EmptyState text="불러오는 중입니다." /> : null}
        {!loading && filteredProjects.length === 0 ? <EmptyWorkspace /> : null}
        {filteredProjects.map((project) => (
          <button
            key={project.project_key}
            type="button"
            onClick={() => onSelect(project.project_key)}
            aria-pressed={project.project_key === selectedKey}
            className={`w-full rounded-2xl border p-4 text-left transition-all duration-200 ${
              project.project_key === selectedKey
                ? "border-indigo-100 bg-indigo-50/80 shadow-sm"
                : "border-transparent bg-white hover:border-slate-200 hover:bg-slate-50"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="min-w-0 break-keep text-sm font-black text-slate-950 max-sm:break-normal">{project.name}</span>
              <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-black text-slate-500 shadow-sm">
                {project.evidence_count.toLocaleString()}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs font-semibold leading-5 text-slate-500">{project.summary}</p>
            <p className="mt-3 text-[11px] font-black text-indigo-600">
              근거 {project.evidence_count.toLocaleString()} · 활동 {project.activity_items.length.toLocaleString()} · 검토 대기 {project.pending_review_count.toLocaleString()}
            </p>
          </button>
        ))}
      </div>
    </aside>
  );
}

function ProjectEvidencePanel({
  evidence,
  sourceFilter,
  onChangeSourceFilter,
}: {
  evidence: ProjectMemory["evidence"];
  sourceFilter: SourceFilter;
  onChangeSourceFilter: (value: SourceFilter) => void;
}) {
  return (
    <section data-testid="project-evidence-panel" className="min-w-0 rounded-3xl border border-white/70 bg-white p-5 shadow-sm">
      <PanelHeading
        title="연결된 원본 근거"
        description="프로젝트와 연결된 Drive, Gmail, Slack, Calendar 기반 원본 자료입니다."
      />
      <div data-testid="project-evidence-tabs" className="mt-4 flex flex-wrap gap-2">
        {SOURCE_FILTERS.map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => onChangeSourceFilter(filter)}
            aria-pressed={sourceFilter === filter}
            className={`rounded-full px-3 py-1.5 text-xs font-black transition ${
              sourceFilter === filter ? "bg-indigo-600 text-white shadow-sm" : "bg-slate-100 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>
      <div className="mt-5 space-y-4">
        {evidence.length === 0 ? (
          <EmptyState text="아직 승인된 원본 근거가 없습니다. Review에서 프로젝트를 선택하고 승인하면 이곳에 쌓입니다." />
        ) : (
          evidence.map((item) => (
            <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md">
              <div className="flex items-start justify-between gap-4">
                <h4 className="line-clamp-2 min-w-0 text-base font-black leading-6 text-slate-950">{item.title}</h4>
                <SourceBadge sourceType={item.source_type} />
              </div>
              <p className="mt-3 line-clamp-3 text-sm font-medium leading-6 text-slate-600">{item.task_summary || item.source_snippet}</p>
              <p className="mt-3 text-sm font-extrabold text-indigo-600">{item.evidence_reason}</p>
              <SourceEvidenceLink href={item.source_url} label={`원본 근거 열기 ${item.title}`} />
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function ProjectActivityPanel({ activityItems }: { activityItems: ProjectMemory["activity_items"] }) {
  return (
    <section data-testid="project-activity-panel" className="min-w-0 rounded-3xl border border-white/70 bg-white p-5 shadow-sm xl:col-start-2 2xl:col-start-auto">
      <PanelHeading
        title="승인된 프로젝트 활동"
        description="Review에서 승인된 결정, 히스토리, 할 일, 타임라인 후보를 프로젝트별로 모은 기록입니다."
      />
      <div data-testid="project-activity-timeline" className="relative mt-5 space-y-4">
        {activityItems.length > 0 ? <span className="absolute bottom-2 left-3 top-2 w-px bg-slate-200" aria-hidden="true" /> : null}
        {activityItems.length === 0 ? (
          <EmptyState text="아직 승인된 활동이 없습니다. Review에서 이 프로젝트를 선택하고 승인하면 여기에 쌓입니다." />
        ) : (
          activityItems.map((item) => (
            <div key={item.id} className="relative pl-9">
              <span className={`absolute left-0 top-5 grid h-6 w-6 place-items-center rounded-full ring-4 ring-white ${activityDotClass(item.item_type)}`}>
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <article className="rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-black ${activityBadgeClass(item.item_type)}`}>{itemTypeLabel(item.item_type)}</span>
                  {item.completed_at ? <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-black text-blue-700">완료</span> : null}
                </div>
                <h4 className="mt-3 line-clamp-2 text-base font-black leading-6 text-slate-950">{item.title}</h4>
                <p className="mt-2 line-clamp-3 text-sm font-medium leading-6 text-slate-600">{item.summary}</p>
                <SourceEvidenceLink href={firstSourceLink(item.source_links)} label={`원본 근거 열기 ${item.title}`} />
              </article>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function PanelHeading({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h3 className="text-lg font-black text-slate-950">{title}</h3>
      <p className="mt-2 text-sm font-medium leading-6 text-slate-500">{description}</p>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div data-testid="project-metric" className="min-w-0 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-center">
      <p className="text-[11px] font-black text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-slate-950">{value.toLocaleString()}</p>
    </div>
  );
}

function SourceBadge({ sourceType }: { sourceType: string }) {
  return <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-black ${sourceBadgeClass(sourceType)}`}>{sourceLabel(sourceType)}</span>;
}

function EmptyWorkspace() {
  return (
    <div className="rounded-2xl border border-dashed border-indigo-100 bg-indigo-50/40 p-4">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white text-indigo-600 shadow-sm">
          <Bot className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p className="text-sm font-black text-slate-950">프로젝트가 없습니다</p>
          <p className="mt-1 text-xs font-semibold leading-5 text-slate-500">새 프로젝트를 만든 뒤 Review에서 근거를 승인해 보세요.</p>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-medium leading-6 text-slate-500">{text}</p>;
}

function SourceEvidenceLink({ href, label }: { href: string; label: string }) {
  if (!href.trim()) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className="mt-4 inline-flex items-center gap-1.5 text-sm font-black text-indigo-600 underline-offset-4 hover:underline"
    >
      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
      원본 근거
      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
    </a>
  );
}

function firstSourceLink(links: string[]) {
  return links.find((link) => link.trim().length > 0) ?? "";
}

function preferredProjectKey(projects: ProjectMemory[]) {
  const projectWithApprovedEvidence = projects.find(
    (project) => project.evidence.length > 0 || project.activity_items.length > 0 || project.timeline_items.length > 0,
  );
  return projectWithApprovedEvidence?.project_key || projects[0]?.project_key || "";
}

function sourceBadgeClass(sourceType: string) {
  if (sourceType === "drive") return "bg-blue-50 text-blue-700";
  if (sourceType === "slack") return "bg-violet-50 text-violet-700";
  if (sourceType === "gmail" || sourceType === "gmail_attachment") return "bg-rose-50 text-rose-700";
  if (sourceType === "calendar") return "bg-emerald-50 text-emerald-700";
  return "bg-slate-100 text-slate-600";
}

function activityBadgeClass(itemType: string) {
  if (itemType === "todo") return "bg-emerald-50 text-emerald-700";
  if (itemType === "timeline_event") return "bg-cyan-50 text-cyan-700";
  if (itemType === "decision_record") return "bg-indigo-50 text-indigo-700";
  if (itemType === "history_event") return "bg-amber-50 text-amber-700";
  return "bg-slate-100 text-slate-600";
}

function activityDotClass(itemType: string) {
  if (itemType === "todo") return "bg-emerald-50 text-emerald-700";
  if (itemType === "timeline_event") return "bg-cyan-50 text-cyan-700";
  if (itemType === "decision_record") return "bg-indigo-50 text-indigo-700";
  if (itemType === "history_event") return "bg-amber-50 text-amber-700";
  return "bg-slate-100 text-slate-600";
}
