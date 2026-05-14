"use client";

import { ExternalLink, FileClock, GitBranch, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { ProjectTimelineItem, ProjectsResponse } from "@/lib/api/types";

type TimelineSource = "Slack" | "Gmail" | "Drive" | "Calendar" | "Source";

type TimelineHistory = {
  id: string;
  time: string;
  source: TimelineSource;
  title: string;
  summary: string;
  history: string;
  status: "approved" | "reviewing";
  sourceUrl: string;
  snippets: { author: string; body: string; time: string }[];
};

type ProjectTimeline = {
  id: string;
  name: string;
  histories: TimelineHistory[];
};

export default function TimelinePage() {
  const [projectTimelines, setProjectTimelines] = useState<ProjectTimeline[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    apiGet<ProjectsResponse>("/api/v1/projects")
      .then((response) => {
        if (!active) return;
        const projects = response.projects.map((project) => ({
          id: project.project_key,
          name: project.name,
          histories: project.timeline_items
            .filter((item) => item.review_status === "approved")
            .map(timelineHistoryFromProjectItem),
        }));
        setProjectTimelines(projects);
        setSelectedProjectId((current) => current || projects[0]?.id || "");
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "Failed to load timeline.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedProject = useMemo(
    () => projectTimelines.find((project) => project.id === selectedProjectId) ?? projectTimelines[0],
    [projectTimelines, selectedProjectId],
  );
  const selectedHistory = selectedProject?.histories.find((history) => history.id === selectedHistoryId);
  const historyCount = selectedProject?.histories.length ?? 0;

  if (loading || !selectedProject) {
    return (
      <div className="reference-dashboard space-y-4">
        <section className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Timeline</p>
            <h1>타임라인</h1>
            <p>{loading ? "승인된 프로젝트 워크플로우를 불러오고 있습니다." : error || "승인된 프로젝트 타임라인 항목이 아직 없습니다."}</p>
          </div>
          <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
            <GitBranch className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            0 histories
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Timeline</p>
            <h1>타임라인</h1>
          <p>등록된 프로젝트에 연결된 승인 타임라인 항목을 시간순으로 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <GitBranch className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {historyCount.toLocaleString()} histories
        </div>
      </section>

      <nav className="panel reference-panel flex gap-2 overflow-x-auto p-2" aria-label="Timeline selector">
        {projectTimelines.map((project) => (
          <button
            key={project.id}
            type="button"
            aria-pressed={project.id === selectedProjectId}
            className={`shrink-0 rounded-md px-3 py-2 text-left text-[13px] font-extrabold transition ${
              project.id === selectedProjectId
                ? "bg-[var(--primary)] text-white shadow-sm ring-2 ring-[var(--primary-soft)]"
                : "bg-[var(--glass-elevated)] text-ink hover:bg-[var(--glass-strong)]"
            }`}
            onClick={() => {
              setSelectedProjectId(project.id);
              setSelectedHistoryId(undefined);
            }}
          >
            {project.name}
          </button>
        ))}
      </nav>

      <section className={`timeline-history-layout ${selectedHistory ? "history-open" : ""}`}>
        <article className="panel reference-panel">
          <div className="border-b border-line pb-4">
            <h2 className="text-[16px] font-extrabold text-ink">{selectedProject.name} 워크플로우</h2>
            <p className="mt-1 text-[13px] text-muted">항목을 열어 어떤 source 문장이 근거인지 확인합니다.</p>
          </div>

          <div className="mt-4 space-y-3">
            {selectedProject.histories.length > 0 ? selectedProject.histories.map((item) => (
              <article key={item.id} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <time className="text-[12px] font-extrabold text-muted">{item.time}</time>
                    <span className="badge blue">{item.source}</span>
                    <span className="badge green">{item.status}</span>
                  </div>
                  <button
                    type="button"
                    aria-pressed={selectedHistoryId === item.id}
                    className={`icon-button small ${selectedHistoryId === item.id ? "active" : ""}`}
                    aria-label={`Open ${item.title}`}
                    onClick={() => setSelectedHistoryId((current) => (current === item.id ? undefined : item.id))}
                  >
                    <FileClock className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
                <h3 className="mt-3 text-[15px] font-extrabold text-ink">{item.title}</h3>
                <p className="mt-1 text-[13px] leading-6 text-muted">{item.summary}</p>
                <div className="mt-3 rounded-md bg-surface-soft px-3 py-2 text-[12px] font-bold leading-5 text-muted">
                  History: {item.history}
                </div>
              </article>
            )) : (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
                이 프로젝트에 승인된 타임라인 항목이 아직 없습니다. Review에서 이 프로젝트를 선택하고 타임라인 후보를 승인하면 여기에 표시됩니다.
              </div>
            )}
          </div>
        </article>

        {selectedHistory ? (
          <aside className="panel reference-panel timeline-history-panel h-fit">
            <div className="flex items-start justify-between gap-3 border-b border-line pb-4">
              <div>
                <p className="text-[12px] font-bold text-[var(--primary-dark)]">{selectedHistory.source} history</p>
                <h2 className="mt-1 text-[16px] font-extrabold text-ink">{selectedHistory.title}</h2>
              </div>
              <button type="button" className="icon-button small" aria-label="Close history" onClick={() => setSelectedHistoryId(undefined)}>
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <p className="mt-4 text-[13px] leading-6 text-muted">{selectedHistory.history}</p>

            {selectedHistory.snippets.length > 0 ? (
              <div className="mt-4 space-y-3">
                {selectedHistory.snippets.map((snippet, index) => (
                  <div key={`${snippet.time}-${index}`} className="rounded-lg border border-line bg-surface-soft p-3">
                    <div className="flex items-center justify-between gap-2 text-[12px] font-bold text-muted">
                      <span>{snippet.author}</span>
                      <span>{snippet.time}</span>
                    </div>
                    <p className="mt-2 text-[13px] leading-6 text-ink">{snippet.body}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
                연결된 source snippet이 없습니다.
              </div>
            )}

            {selectedHistory.sourceUrl ? (
              <a
                href={selectedHistory.sourceUrl}
                className="mt-4 inline-flex items-center gap-2 text-[12px] font-extrabold text-[var(--primary-dark)] underline-offset-4 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Open source
              </a>
            ) : null}
          </aside>
        ) : null}
      </section>
    </div>
  );
}

function timelineHistoryFromProjectItem(item: ProjectTimelineItem): TimelineHistory {
  return {
    id: item.id,
    time: formatTime(item.created_at),
    source: sourceFromLinks(item.source_links),
    title: item.title,
    summary: item.summary,
    history: item.summary || "No approved timeline summary.",
    status: item.review_status === "approved" ? "approved" : "reviewing",
    sourceUrl: item.source_links[0] ?? "",
    snippets: item.source_snippets.map((snippet) => ({
      author: `${sourceFromLinks(item.source_links)} evidence · ${item.evidence_reason || "승인된 프로젝트 근거"}`,
      body: snippet,
      time: formatTime(item.created_at),
    })),
  };
}

function sourceFromLinks(links: string[]): TimelineSource {
  const joined = links.join(" ").toLowerCase();
  if (joined.includes("slack")) return "Slack";
  if (joined.includes("gmail") || joined.includes("mail")) return "Gmail";
  if (joined.includes("drive") || joined.includes("docs.google")) return "Drive";
  if (joined.includes("calendar")) return "Calendar";
  return "Source";
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(date);
}
