"use client";

import {
  CalendarDays,
  ChevronDown,
  Code2,
  ExternalLink,
  Eye,
  FileClock,
  FileText,
  GitBranch,
  Mail,
  MessageSquare,
  RotateCcw,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { ProjectTimelineItem, ProjectsResponse } from "@/lib/api/types";
import Image from "next/image";
import todoIcon from "@/app/timeline/icons/todo.png";
import slackIcon from "@/app/timeline/icons/slack.svg";
import gmailIcon from "@/app/timeline/icons/gmail.png";
import driveIcon from "@/app/timeline/icons/drive.svg";
import calendarIcon from "@/app/timeline/icons/calendar.svg";

type TimelineSource = "Slack" | "Gmail" | "Drive" | "Calendar" | "Source";
type PeriodFilter = "all" | "7d" | "30d";
type SourceFilter = "all" | TimelineSource;
type StatusFilter = "all" | TimelineHistory["status"];

type TimelineHistory = {
  id: string;
  itemType: string;
  createdAt: string;
  time: string;
  source: TimelineSource;
  title: string;
  summary: string;
  history: string;
  status: "approved" | "reviewing" | "완료";
  sourceUrl: string;
  preview: string;
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
  const [expandedDateLabel, setExpandedDateLabel] = useState<string | null | undefined>();
  const [expandedItemGroups, setExpandedItemGroups] = useState<Set<string>>(() => new Set());
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>("all");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
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
        const defaultProject = firstProjectWithHistories(projects);
        setProjectTimelines(projects);
        setSelectedProjectId((current) => current || defaultProject?.id || "");
        setExpandedDateLabel((current) => current ?? firstDateLabel(defaultProject?.histories ?? []));
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
  const filteredHistories = useMemo(
    () => filterHistories(selectedProject?.histories ?? [], periodFilter, sourceFilter, statusFilter),
    [periodFilter, selectedProject?.histories, sourceFilter, statusFilter],
  );
  const selectedHistory = selectedProject?.histories.find((history) => history.id === selectedHistoryId);
  const historyCount = selectedProject?.histories.length ?? 0;
  const groupedHistories = useMemo(
    () => groupHistoriesByDate(filteredHistories),
    [filteredHistories],
  );

  useEffect(() => {
    const firstLabel = firstDateLabel(filteredHistories);
    setExpandedDateLabel((current) => {
      if (current && groupedHistories.some((group) => group.dateLabel === current)) {
        return current;
      }
      return firstLabel;
    });
    setExpandedItemGroups(new Set());
  }, [filteredHistories, groupedHistories]);

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
              setExpandedDateLabel(firstDateLabel(project.histories));
              setExpandedItemGroups(new Set());
            }}
          >
            {project.name}
          </button>
        ))}
      </nav>

      <section className={`timeline-history-layout ${selectedHistory ? "history-open" : ""}`}>
        <TimelineListPanel
          histories={filteredHistories}
          groupedHistories={groupedHistories}
          expandedDateLabel={expandedDateLabel}
          expandedItemGroups={expandedItemGroups}
          selectedHistoryId={selectedHistoryId}
          periodFilter={periodFilter}
          sourceFilter={sourceFilter}
          statusFilter={statusFilter}
          onChangePeriod={setPeriodFilter}
          onChangeSource={setSourceFilter}
          onChangeStatus={setStatusFilter}
          onResetFilters={() => {
            setPeriodFilter("all");
            setSourceFilter("all");
            setStatusFilter("all");
          }}
          onToggleDate={(dateLabel) => {
            setExpandedDateLabel((current) => (current === dateLabel ? null : dateLabel));
            setExpandedItemGroups((current) => {
              const next = new Set(current);
              next.delete(dateLabel);
              return next;
            });
            setSelectedHistoryId(undefined);
          }}
          onToggleMore={(dateLabel) => {
            setExpandedItemGroups((current) => {
              const next = new Set(current);
              if (next.has(dateLabel)) {
                next.delete(dateLabel);
              } else {
                next.add(dateLabel);
              }
              return next;
            });
          }}
          onSelectHistory={(historyId) => {
            setSelectedHistoryId((current) => (current === historyId ? undefined : historyId));
          }}
        />

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
                target="_blank"
                rel="noopener noreferrer"
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

function TimelineListPanel({
  histories,
  groupedHistories,
  expandedDateLabel,
  expandedItemGroups,
  selectedHistoryId,
  periodFilter,
  sourceFilter,
  statusFilter,
  onChangePeriod,
  onChangeSource,
  onChangeStatus,
  onResetFilters,
  onToggleDate,
  onToggleMore,
  onSelectHistory,
}: {
  histories: TimelineHistory[];
  groupedHistories: ReturnType<typeof groupHistoriesByDate>;
  expandedDateLabel: string | null | undefined;
  expandedItemGroups: Set<string>;
  selectedHistoryId?: string;
  periodFilter: PeriodFilter;
  sourceFilter: SourceFilter;
  statusFilter: StatusFilter;
  onChangePeriod: (value: PeriodFilter) => void;
  onChangeSource: (value: SourceFilter) => void;
  onChangeStatus: (value: StatusFilter) => void;
  onResetFilters: () => void;
  onToggleDate: (dateLabel: string) => void;
  onToggleMore: (dateLabel: string) => void;
  onSelectHistory: (historyId: string) => void;
}) {
  return (
    <article className="panel reference-panel overflow-hidden p-0">
      <TimelineSummaryBar
        count={histories.length}
        periodFilter={periodFilter}
        sourceFilter={sourceFilter}
        statusFilter={statusFilter}
        onChangePeriod={onChangePeriod}
        onChangeSource={onChangeSource}
        onChangeStatus={onChangeStatus}
        onResetFilters={onResetFilters}
      />

      <div className="space-y-4 border-t border-line bg-white px-3 py-4 sm:px-5">
        {histories.length > 0 ? (
          groupedHistories.map((group) => (
            <TimelineDateGroup
              key={group.dateLabel}
              group={group}
              isExpanded={expandedDateLabel === group.dateLabel}
              isShowingAll={expandedItemGroups.has(group.dateLabel)}
              selectedHistoryId={selectedHistoryId}
              onToggleDate={onToggleDate}
              onToggleMore={onToggleMore}
              onSelectHistory={onSelectHistory}
            />
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-line bg-surface-soft p-5 text-[13px] text-muted">
            조건에 맞는 승인 타임라인 항목이 없습니다. 필터를 초기화하거나 Review에서 프로젝트 타임라인 후보를 승인해 주세요.
          </div>
        )}
      </div>
    </article>
  );
}

function TimelineSummaryBar({
  count,
  periodFilter,
  sourceFilter,
  statusFilter,
  onChangePeriod,
  onChangeSource,
  onChangeStatus,
  onResetFilters,
}: {
  count: number;
  periodFilter: PeriodFilter;
  sourceFilter: SourceFilter;
  statusFilter: StatusFilter;
  onChangePeriod: (value: PeriodFilter) => void;
  onChangeSource: (value: SourceFilter) => void;
  onChangeStatus: (value: StatusFilter) => void;
  onResetFilters: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 bg-[var(--glass-elevated)] px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary-dark)]">
          <CalendarDays className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p className="text-[12px] font-bold text-muted">전체 히스토리</p>
          <h2 className="text-[18px] font-extrabold leading-6 text-ink">{count.toLocaleString()}건</h2>
        </div>
      </div>
      <TimelineFilterControls
        periodFilter={periodFilter}
        sourceFilter={sourceFilter}
        statusFilter={statusFilter}
        onChangePeriod={onChangePeriod}
        onChangeSource={onChangeSource}
        onChangeStatus={onChangeStatus}
        onResetFilters={onResetFilters}
      />
    </div>
  );
}

function TimelineFilterControls({
  periodFilter,
  sourceFilter,
  statusFilter,
  onChangePeriod,
  onChangeSource,
  onChangeStatus,
  onResetFilters,
}: {
  periodFilter: PeriodFilter;
  sourceFilter: SourceFilter;
  statusFilter: StatusFilter;
  onChangePeriod: (value: PeriodFilter) => void;
  onChangeSource: (value: SourceFilter) => void;
  onChangeStatus: (value: StatusFilter) => void;
  onResetFilters: () => void;
}) {
  const selectClass =
    "h-9 rounded-md border border-line bg-white px-3 text-[12px] font-bold text-ink shadow-xs outline-none transition hover:border-[var(--line-hover)] focus:border-[var(--primary)]";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="sr-only" htmlFor="timeline-period-filter">
        기간 필터
      </label>
      <select
        id="timeline-period-filter"
        aria-label="기간 필터"
        className={selectClass}
        value={periodFilter}
        onChange={(event) => onChangePeriod(event.target.value as PeriodFilter)}
      >
        <option value="all">전체 기간</option>
        <option value="7d">최근 7일</option>
        <option value="30d">최근 30일</option>
      </select>
      <label className="sr-only" htmlFor="timeline-source-filter">
        소스 필터
      </label>
      <select
        id="timeline-source-filter"
        aria-label="소스 필터"
        className={selectClass}
        value={sourceFilter}
        onChange={(event) => onChangeSource(event.target.value as SourceFilter)}
      >
        <option value="all">소스 전체</option>
        <option value="Slack">Slack</option>
        <option value="Gmail">Gmail</option>
        <option value="Drive">Drive</option>
        <option value="Calendar">Calendar</option>
        <option value="Source">Source</option>
      </select>
      <label className="sr-only" htmlFor="timeline-status-filter">
        상태 필터
      </label>
      <select
        id="timeline-status-filter"
        aria-label="상태 필터"
        className={selectClass}
        value={statusFilter}
        onChange={(event) => onChangeStatus(event.target.value as StatusFilter)}
      >
        <option value="all">상태 전체</option>
        <option value="approved">approved</option>
        <option value="reviewing">reviewing</option>
        <option value="완료">완료</option>
      </select>
      <button
        type="button"
        onClick={onResetFilters}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-[12px] font-extrabold text-ink shadow-xs transition hover:border-[var(--line-hover)] hover:bg-surface-soft"
      >
        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
        필터 초기화
      </button>
    </div>
  );
}

function TimelineDateGroup({
  group,
  isExpanded,
  isShowingAll,
  selectedHistoryId,
  onToggleDate,
  onToggleMore,
  onSelectHistory,
}: {
  group: ReturnType<typeof groupHistoriesByDate>[number];
  isExpanded: boolean;
  isShowingAll: boolean;
  selectedHistoryId?: string;
  onToggleDate: (dateLabel: string) => void;
  onToggleMore: (dateLabel: string) => void;
  onSelectHistory: (historyId: string) => void;
}) {
  const visibleItems = isShowingAll ? group.items : group.items.slice(0, 3);
  const hiddenCount = group.items.length - visibleItems.length;

  return (
    <section className="relative pl-8">
      <span className="absolute left-3 top-4 h-full border-l border-dashed border-slate-200" aria-hidden="true" />
      <span
        className={`absolute left-[7px] top-[18px] z-10 grid h-4 w-4 place-items-center rounded-full border bg-white ${
          isExpanded ? "border-[var(--primary)] text-[var(--primary)]" : "border-slate-300 text-muted"
        }`}
        aria-hidden="true"
      >
        <span className={`h-1.5 w-1.5 rounded-full ${isExpanded ? "bg-[var(--primary)]" : "bg-slate-300"}`} />
      </span>
      <button
        type="button"
        aria-expanded={isExpanded}
        className={`group flex w-full items-center justify-between gap-3 rounded-lg border px-4 py-3 text-left shadow-xs transition ${
          isExpanded
            ? "border-[var(--primary-soft)] bg-white text-ink"
            : "border-line bg-[var(--glass-elevated)] text-ink hover:border-[var(--line-hover)] hover:bg-white"
        }`}
        onClick={() => onToggleDate(group.dateLabel)}
      >
        <span className="flex min-w-0 items-center gap-2">
          <h3 className="truncate text-[15px] font-extrabold text-ink">{group.dateLabel}</h3>
          <span className="rounded-full bg-[var(--primary-soft)] px-2 py-0.5 text-[11px] font-extrabold text-[var(--primary-dark)]">
            {group.items.length.toLocaleString()}건
          </span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${isExpanded ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      {isExpanded ? (
        <div className="mt-3 space-y-2">
          {visibleItems.map((item) => (
            <TimelineEventRow
              key={item.id}
              item={item}
              isSelected={selectedHistoryId === item.id}
              onSelectHistory={onSelectHistory}
            />
          ))}
          {group.items.length > 3 ? (
            <button
              type="button"
              className="ml-1 inline-flex items-center gap-1.5 rounded-md px-1 py-1 text-[12px] font-extrabold text-[var(--primary-dark)] hover:underline"
              onClick={() => onToggleMore(group.dateLabel)}
            >
              {isShowingAll ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                  접기
                </>
              ) : (
                <>
                  {hiddenCount.toLocaleString()}건 더 보기
                  <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                </>
              )}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function TimelineEventRow({
  item,
  isSelected,
  onSelectHistory,
}: {
  item: TimelineHistory;
  isSelected: boolean;
  onSelectHistory: (historyId: string) => void;
}) {
  return (
    <article className="grid gap-3 rounded-lg border border-line bg-white p-3 shadow-xs transition hover:border-[var(--line-hover)] hover:shadow-panel-hover sm:grid-cols-[38px_minmax(0,1fr)_auto] sm:items-center">
      <span className="grid h-9 w-9 place-items-center rounded-lg bg-surface-soft text-[var(--primary-dark)]">
        <TimelineSourceIcon item={item} />
      </span>
      <div className="min-w-0">
        <h3 className="line-clamp-2 text-[14px] font-extrabold leading-5 text-ink">{item.title}</h3>
        <p className="mt-1 truncate text-[12px] font-medium text-muted">{item.preview}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
        <time className="text-[12px] font-bold text-muted">{item.time}</time>
        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-extrabold text-slate-600">
          {item.source}
        </span>
        <span className={`rounded-md border px-2 py-1 text-[11px] font-extrabold ${statusChipClass(item.status)}`}>
          {item.status}
        </span>
        <button
          type="button"
          aria-pressed={isSelected}
          className={`icon-button small shrink-0 ${isSelected ? "active" : ""}`}
          aria-label={`Open ${item.title}`}
          onClick={() => onSelectHistory(item.id)}
        >
          <Eye className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

const sourceIconImages: Record<string, string> = {
  Slack: slackIcon,
  Gmail: gmailIcon,
  Drive: driveIcon,
  Calendar: calendarIcon,
};

function TimelineSourceIcon({ item }: { item: TimelineHistory }) {
  const src = sourceIconImages[item.source] ?? todoIcon;

  return (
    <Image
      src={src}
      alt=""
      width={18}
      height={18}
      className="h-4.5 w-4.5 object-contain"
      aria-hidden="true"
    />
  );
}


function timelineHistoryFromProjectItem(item: ProjectTimelineItem): TimelineHistory {
  const occurredAt = item.occurred_at || item.created_at;
  const source = sourceFromLinks(item.source_links);
  return {
    id: item.id,
    itemType: item.item_type,
    createdAt: occurredAt,
    time: formatTime(occurredAt),
    source,
    title: item.title,
    summary: item.summary,
    history: item.summary || "No approved timeline summary.",
    status: item.completed_at ? "완료" : item.review_status === "approved" ? "approved" : "reviewing",
    sourceUrl: item.source_links[0] ?? "",
    preview: previewForProjectItem(item, source),
    snippets: item.source_snippets.map((snippet) => ({
      author: `${source} evidence · ${item.evidence_reason || "승인된 프로젝트 근거"}`,
      body: snippet,
      time: formatTime(occurredAt),
    })),
  };
}

function groupHistoriesByDate(histories: TimelineHistory[]) {
  const groups = new Map<string, TimelineHistory[]>();
  for (const history of [...histories].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))) {
    const label = formatDate(history.createdAt);
    groups.set(label, [...(groups.get(label) ?? []), history]);
  }
  return Array.from(groups.entries()).map(([dateLabel, items]) => ({ dateLabel, items }));
}

function firstDateLabel(histories: TimelineHistory[]) {
  return groupHistoriesByDate(histories)[0]?.dateLabel ?? null;
}

function firstProjectWithHistories(projects: ProjectTimeline[]) {
  return projects.find((project) => project.histories.length > 0) ?? projects[0];
}

function sourceFromLinks(links: string[]): TimelineSource {
  const joined = links.join(" ").toLowerCase();
  if (joined.includes("slack")) return "Slack";
  if (joined.includes("gmail") || joined.includes("mail")) return "Gmail";
  if (joined.includes("drive") || joined.includes("docs.google")) return "Drive";
  if (joined.includes("calendar")) return "Calendar";
  return "Source";
}

function statusChipClass(status: TimelineHistory["status"]) {
  if (status === "approved") return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (status === "완료") return "border-blue-100 bg-blue-50 text-blue-700";
  return "border-amber-100 bg-amber-50 text-amber-700";
}

function previewForProjectItem(item: ProjectTimelineItem, source: TimelineSource) {
  const snippet = item.source_snippets.find((value) => value.trim().length > 0);
  if (snippet) return snippet;
  if (item.summary) return item.summary;
  return `${source} 근거가 연결된 승인 타임라인 항목입니다.`;
}

function filterHistories(
  histories: TimelineHistory[],
  periodFilter: PeriodFilter,
  sourceFilter: SourceFilter,
  statusFilter: StatusFilter,
) {
  const now = Date.now();
  return histories.filter((history) => {
    if (sourceFilter !== "all" && history.source !== sourceFilter) return false;
    if (statusFilter !== "all" && history.status !== statusFilter) return false;
    if (periodFilter === "all") return true;
    const timestamp = Date.parse(history.createdAt);
    if (Number.isNaN(timestamp)) return true;
    const days = periodFilter === "7d" ? 7 : 30;
    return now - timestamp <= days * 24 * 60 * 60 * 1000;
  });
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Seoul",
  }).format(date);
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "날짜 미상";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Asia/Seoul",
  }).format(date);
}
