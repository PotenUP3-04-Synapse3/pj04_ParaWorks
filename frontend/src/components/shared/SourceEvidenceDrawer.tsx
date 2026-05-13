"use client";

import { ExternalLink, FileText, GitBranch, ShieldCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { ReviewSourceEvidence } from "@/lib/api/types";

type SourceEvidenceDrawerProps = {
  evidence?: ReviewSourceEvidence[];
  links?: string[];
  snippets?: string[];
  itemTitle?: string;
  agentRunId?: number | null;
};

export function SourceEvidenceDrawer({
  evidence,
  links = [],
  snippets = [],
  itemTitle,
  agentRunId,
}: SourceEvidenceDrawerProps) {
  const [open, setOpen] = useState(false);
  const evidenceRows = useMemo(
    () => evidence && evidence.length > 0 ? evidence : fallbackEvidenceRows(links, snippets, agentRunId),
    [agentRunId, evidence, links, snippets],
  );
  const effectiveAgentRunId = agentRunId ?? evidenceRows.find((row) => row.agent_run_id)?.agent_run_id;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-[var(--ink)] shadow-sm hover:bg-[var(--glass-strong)]"
      >
        <FileText className="h-4 w-4" aria-hidden="true" />
        근거 보기
      </button>
      {open ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-black/40 backdrop-blur-sm"
            aria-label="출처 근거 닫기"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute inset-y-0 right-0 flex w-full max-w-2xl flex-col border-l border-[var(--line-soft)] bg-[var(--surface)] shadow-2xl">
            <div className="border-b border-[var(--line-soft)] px-5 py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                    Source Evidence
                  </p>
                  <h2 className="mt-1 truncate text-base font-semibold text-[var(--ink)]">
                    {itemTitle || "검토 후보 근거"}
                  </h2>
                  <p className="mt-1 text-sm text-[var(--ink-muted)]">
                    연결된 snippet {evidenceRows.length.toLocaleString("ko-KR")}개를 기준으로 검토합니다.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-[var(--line-soft)] text-[var(--ink-muted)] hover:bg-[var(--glass-strong)] hover:text-[var(--ink)]"
                  aria-label="닫기"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              {effectiveAgentRunId ? (
                <a
                  href={`/agent-runs/${effectiveAgentRunId}`}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 py-2 text-xs font-semibold text-[var(--workspace-rail-active)] hover:bg-[var(--glass-strong)]"
                >
                  <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
                  Agent Run #{effectiveAgentRunId}에서 생성
                </a>
              ) : null}
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <div className="space-y-4">
                {evidenceRows.map((row) => (
                  <section
                    key={`${row.source_url || row.source_id || row.index}-${row.index}`}
                    className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-4 shadow-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[var(--workspace-rail-active)] px-2.5 py-1 text-xs font-semibold text-white">
                        Rank {row.rank}
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                        <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                        {row.permission_level}
                      </span>
                      <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                        신뢰도 {Math.round(row.confidence_score * 100)}%
                      </span>
                      {row.source_type ? (
                        <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                          {sourceTypeLabel(row.source_type)}
                        </span>
                      ) : null}
                      {row.parser_status ? (
                        <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                          parser {row.parser_status}
                        </span>
                      ) : null}
                      {row.importance_score > 0 ? (
                        <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                          중요도 {row.importance_score}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--ink)]">
                      {row.author ? (
                        <span className="mr-1.5 inline-flex items-center rounded-md bg-[var(--workspace-rail-active)]/10 px-1.5 py-0.5 text-xs font-bold text-[var(--workspace-rail-active)]">
                          {row.author}
                        </span>
                      ) : null}
                      {row.source_snippet || "표시할 근거 snippet이 없습니다."}
                    </p>
                    {row.evidence_reason || row.section_path ? (
                      <div className="mt-3 rounded-md border border-[var(--line-soft)] bg-[var(--glass-strong)] px-3 py-2 text-xs leading-5 text-[var(--ink-muted)]">
                        {row.evidence_reason ? <p>{row.evidence_reason}</p> : null}
                        {row.section_path ? <p className="mt-1 font-semibold">위치: {row.section_path}</p> : null}
                      </div>
                    ) : null}
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-[10px] font-bold text-[var(--ink-muted)] uppercase tracking-tight">
                      {row.source_id ? <span className="truncate">Source ID: {row.source_id}</span> : null}
                      {row.timestamp ? <span>Time: {row.timestamp}</span> : null}
                    </div>
                    {row.source_url ? (
                      <a
                        href={row.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[var(--workspace-rail-active)] underline-offset-4 hover:underline"
                      >
                        원문 열기
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      </a>
                    ) : null}
                  </section>
                ))}
                {evidenceRows.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-[var(--line-soft)] bg-[var(--glass-elevated)] p-4 text-sm text-[var(--ink-muted)]">
                    이 항목과 연결된 출처 snippet이 없습니다. 근거가 없는 후보는 승인하지 않는 것이 기본 정책입니다.
                  </p>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}

function fallbackEvidenceRows(
  links: string[],
  snippets: string[],
  agentRunId?: number | null,
): ReviewSourceEvidence[] {
  const count = Math.max(links.length, snippets.length);
  return Array.from({ length: count }, (_, index) => ({
    index: index + 1,
    rank: index + 1,
    source_id: null,
    source_url: links[index] ?? null,
    source_type: null,
    source_snippet: snippets[index] ?? "",
    permission_level: "unknown",
    confidence_score: 0,
    importance_score: 0,
    timestamp: null,
    author: null,
    agent_run_id: agentRunId ?? null,
    parser_status: null,
    section_path: null,
    evidence_reason: null,
  }));
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === "gmail") return "Gmail";
  if (sourceType === "gmail_attachment") return "Gmail 첨부";
  if (sourceType === "drive") return "Drive";
  if (sourceType === "calendar") return "Calendar";
  if (sourceType === "slack") return "Slack";
  return sourceType;
}
