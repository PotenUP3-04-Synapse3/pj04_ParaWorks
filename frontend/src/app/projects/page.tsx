"use client";

import { CheckCircle2, ExternalLink, FolderKanban, Plus, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
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

function sourceLabel(sourceType: string) {
  return {
    slack: "Slack",
    gmail: "Gmail",
    gmail_attachment: "Gmail 첨부",
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
        setSelectedKey(nextProjects[0]?.project_key || "");
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

  return (
    <div className="reference-dashboard space-y-5">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Project Workspace</p>
          <h1>프로젝트</h1>
          <p>사용자가 만든 프로젝트를 기준으로 Slack, Gmail, Drive, Calendar 근거와 승인된 활동을 모아봅니다.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void loadProjects()}
            disabled={loading}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink shadow-sm disabled:opacity-60"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            새로고침
          </button>
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-[var(--primary)] px-4 text-sm font-semibold text-white shadow-sm"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />새 프로젝트
          </button>
        </div>
      </section>

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

      {isCreating ? (
        <section className="panel reference-panel">
          <div className="grid gap-3 md:grid-cols-[minmax(0,280px)_1fr_auto] md:items-end">
            <label className="text-sm font-bold text-ink">
              프로젝트명
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="예: 고객 포털 개편"
                className="mt-1 h-10 w-full rounded-lg border border-[var(--line-soft)] px-3 text-sm font-normal outline-none focus:border-[var(--primary)]"
              />
            </label>
            <label className="text-sm font-bold text-ink">
              간단한 설명
              <input
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                placeholder="프로젝트 목적과 주요 키워드를 적어 주세요."
                className="mt-1 h-10 w-full rounded-lg border border-[var(--line-soft)] px-3 text-sm font-normal outline-none focus:border-[var(--primary)]"
              />
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void createProject()}
                disabled={createPending}
                className="h-10 rounded-lg bg-[var(--primary)] px-4 text-sm font-bold text-white disabled:opacity-60"
              >
                생성
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="h-10 rounded-lg border border-[var(--line-soft)] px-4 text-sm font-bold"
              >
                취소
              </button>
            </div>
          </div>
          {createError ? <p className="mt-3 text-sm font-semibold text-red-700">{createError}</p> : null}
        </section>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="panel reference-panel">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-extrabold text-ink">프로젝트 목록</h2>
              <p className="mt-1 text-xs text-muted">{projects.length.toLocaleString()}개 프로젝트</p>
            </div>
            <FolderKanban className="h-5 w-5 text-[var(--primary)]" aria-hidden="true" />
          </div>
          <label className="mt-4 flex h-10 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 text-sm">
            <Search className="h-4 w-4 text-muted" aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="프로젝트 검색"
              className="min-w-0 flex-1 bg-transparent outline-none"
            />
          </label>
          <div className="mt-4 space-y-2">
            {loading ? <p className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">불러오는 중입니다.</p> : null}
            {!loading && filteredProjects.length === 0 ? (
              <p className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
                아직 표시할 프로젝트가 없습니다. 새 프로젝트를 먼저 만들어 주세요.
              </p>
            ) : null}
            {filteredProjects.map((project) => (
              <button
                key={project.project_key}
                type="button"
                onClick={() => setSelectedKey(project.project_key)}
                className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                  project.project_key === selectedKey
                    ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                    : "border-[var(--line-soft)] bg-white hover:bg-surface-soft"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-extrabold text-ink">{project.name}</span>
                  <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-muted">
                    {project.evidence_count + project.activity_items.length}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{project.summary}</p>
              </button>
            ))}
          </div>
        </aside>

        <main className="space-y-5">
          {!selectedProject ? (
            <section className="panel reference-panel">
              <h2 className="text-lg font-extrabold text-ink">프로젝트를 선택해 주세요</h2>
              <p className="mt-2 text-sm text-muted">프로젝트를 만들면 이곳에서 근거와 승인된 활동을 확인할 수 있습니다.</p>
            </section>
          ) : (
            <>
              <section className="panel reference-panel">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase text-muted">{selectedProject.project_key}</p>
                    <h2 className="mt-1 text-2xl font-extrabold text-ink">{selectedProject.name}</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{selectedProject.summary}</p>
                  </div>
                  <div className="grid w-full grid-cols-1 gap-2 text-center sm:w-auto sm:grid-cols-3">
                    <Metric label="근거" value={selectedProject.evidence_count} />
                    <Metric label="활동" value={selectedProject.activity_items.length} />
                    <Metric label="검토 대기" value={selectedProject.pending_review_count} />
                  </div>
                </div>
              </section>

              <section className="grid gap-5 lg:grid-cols-2">
                <ProjectPanel title="연결된 원본 근거">
                  {selectedProject.evidence.length === 0 ? (
                    <EmptyState text="아직 승인된 원본 근거가 없습니다. Review에서 프로젝트를 선택하고 승인하면 이곳에 쌓입니다." />
                  ) : (
                    selectedProject.evidence.map((item) => (
                      <article key={item.id} className="rounded-lg border border-line bg-white p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="min-w-0 truncate text-sm font-extrabold text-ink">{item.title}</h3>
                          <span className="rounded-full bg-surface-soft px-2 py-0.5 text-[11px] font-bold text-muted">
                            {sourceLabel(item.source_type)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-muted">{item.task_summary}</p>
                        <p className="mt-2 text-xs font-semibold text-[var(--primary-dark)]">{item.evidence_reason}</p>
                        <SourceEvidenceLink href={item.source_url} label={`원본 근거 열기 ${item.title}`} />
                      </article>
                    ))
                  )}
                </ProjectPanel>

                <ProjectPanel
                  title="승인된 프로젝트 활동"
                  description="Review에서 승인된 결정, 히스토리, 할 일, 타임라인 후보를 프로젝트별로 모은 기록입니다. 각 항목은 근거와 함께 보존되며 RAG 검색, 회고, 진행 상황 파악에 사용됩니다."
                >
                  {selectedProject.activity_items.length === 0 ? (
                    <EmptyState text="아직 승인된 활동이 없습니다. Review에서 이 프로젝트를 선택하고 승인하면 여기에 쌓입니다." />
                  ) : (
                    selectedProject.activity_items.map((item) => (
                      <article key={item.id} className="rounded-lg border border-line bg-white p-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700">
                            {itemTypeLabel(item.item_type)}
                          </span>
                        </div>
                        <h3 className="mt-2 text-sm font-extrabold text-ink">{item.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-muted">{item.summary}</p>
                        <SourceEvidenceLink href={firstSourceLink(item.source_links)} label={`원본 근거 열기 ${item.title}`} />
                      </article>
                    ))
                  )}
                </ProjectPanel>
              </section>
            </>
          )}
        </main>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div data-testid="project-metric" className="min-w-0 rounded-lg border border-line bg-white px-3 py-2">
      <p className="text-[11px] font-bold text-muted">{label}</p>
      <p className="mt-1 text-lg font-extrabold text-ink">{value.toLocaleString()}</p>
    </div>
  );
}

function ProjectPanel({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="panel reference-panel">
      <h2 className="text-base font-extrabold text-ink">{title}</h2>
      {description ? <p className="mt-2 text-sm leading-6 text-muted">{description}</p> : null}
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-lg border border-dashed border-line p-4 text-sm leading-6 text-muted">{text}</p>;
}

function firstSourceLink(links: string[]) {
  return links.find((link) => link.trim().length > 0) ?? "";
}

function SourceEvidenceLink({ href, label }: { href: string; label: string }) {
  if (!href.trim()) {
    return null;
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className="mt-3 inline-flex items-center gap-1.5 text-xs font-extrabold text-[var(--primary-dark)] underline-offset-4 hover:underline"
    >
      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
      원본 근거
    </a>
  );
}
