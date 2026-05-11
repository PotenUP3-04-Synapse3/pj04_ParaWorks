"use client";

import { Bot, CheckCircle2, CircleDollarSign, Clock3, Database, FileText, KeyRound, Link2, Search, ShieldAlert, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type { AskResponse, RagIndexingJobSummary, RagIndexingSummaryResponse, SearchResponse } from "@/lib/api/types";

const DEFAULT_QUESTION = "Redis 작업 상태는 어떻게 관리되고 있나요?";

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageFallback />}>
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q")?.trim() || DEFAULT_QUESTION;
  const [query, setQuery] = useState(initialQuery);
  const [searchResponse, setSearchResponse] = useState<SearchResponse>();
  const [askResponse, setAskResponse] = useState<AskResponse>();
  const [ragIndexing, setRagIndexing] = useState<RagIndexingSummaryResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const runMemoryQuery = useCallback(async (nextQuery: string) => {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) return;

    setLoading(true);
    setError(undefined);
    try {
      const [askResult, searchResult] = await Promise.all([
        apiPost<AskResponse>("/api/v1/ask", { question: trimmedQuery }),
        apiPost<SearchResponse>("/api/v1/search", { query: trimmedQuery }),
      ]);
      setAskResponse(askResult);
      setSearchResponse(searchResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "회사 메모리 검색에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runMemoryQuery(query);
  }

  useEffect(() => {
    setQuery(initialQuery);
    void runMemoryQuery(initialQuery);
  }, [initialQuery, runMemoryQuery]);

  useEffect(() => {
    let active = true;
    apiGet<RagIndexingSummaryResponse>("/api/v1/rag/indexing/summary")
      .then((result) => {
        if (active) setRagIndexing(result);
      })
      .catch(() => {
        if (active) setRagIndexing(undefined);
      });
    return () => {
      active = false;
    };
  }, []);

  const permissionNotice = askResponse?.permission_notice ?? searchResponse?.permission_notice;
  const answerCitations = askResponse?.citations ?? [];

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Company Memory</p>
          <h1>Ask 워크스페이스</h1>
          <p>승인된 지식과 접근 가능한 source evidence를 바탕으로 질문하고 근거를 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Bot className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {searchResponse?.retrieval_backend === "pgvector" ? "pgvector search" : "deterministic search"}
        </div>
      </div>

      <MemoryFreshnessPanel summary={ragIndexing} />

      <form onSubmit={submit} className="panel reference-panel">
        <label htmlFor="query" className="text-[13px] font-extrabold">질문</label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="h-11 min-w-0 flex-1 rounded-lg border border-line bg-[var(--glass-elevated)] px-3 text-[13px] outline-none focus:border-[var(--primary)]"
            placeholder="예: 지난주 Redis 역할 논의가 있었나요?"
          />
          <button type="submit" disabled={loading} className="row-action gap-2 px-4 disabled:bg-neutral-300">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {loading ? "답변 생성 중" : "AI에게 질문"}
          </button>
        </div>
      </form>

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-800">{error}</div> : null}

      {permissionNotice ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-900">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-extrabold">권한 때문에 숨겨진 근거가 있습니다.</p>
            <p className="mt-1 text-amber-800">{permissionNotice}</p>
            {searchResponse?.hidden_match_count ? (
              <p className="mt-1 text-[12px] text-amber-800">
                현재 권한에서 숨겨진 근거 {searchResponse.hidden_match_count.toLocaleString()}개
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]">
        <article className="panel reference-panel">
          <div className="flex items-center gap-2 border-b border-line pb-4">
            <Bot className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            <h2 className="text-[15px] font-extrabold">AI 답변</h2>
          </div>

          <div className="space-y-4 pt-4">
            {askResponse ? (
              <>
                <p className="text-[15px] leading-7">{askResponse.answer}</p>
                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricCard icon={FileText} label="답변 근거" value={`${askResponse.source_links.length.toLocaleString()}개`} />
                  <MetricCard icon={ShieldAlert} label="숨겨진 근거" value={`${askResponse.hidden_match_count.toLocaleString()}개`} />
                  <MetricCard icon={KeyRound} label="조회 권한" value={askResponse.permission_level} />
                </div>

                <div>
                  <div className="mb-2 flex items-center gap-2 text-[13px] font-extrabold">
                    <Link2 className="h-4 w-4" aria-hidden="true" />
                    답변 근거
                  </div>
                  <div className="space-y-2">
                    {answerCitations.map((citation, index) => (
                      <a key={`${citation.source_id}-${index}`} href={citation.source_url} target="_blank" rel="noreferrer" className="block rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[13px] hover:bg-[var(--glass-strong)]">
                        <span className="font-bold text-[var(--primary-dark)]">근거 {index + 1}</span>
                        <span className="mt-1 block text-[12px] text-muted">{citation.source_id}</span>
                        <span className="mt-1 block text-[12px] text-muted">
                          score {citation.relevance_score.toFixed(2)}
                          {citation.matched_terms.length ? ` · ${citation.matched_terms.join(", ")}` : ""}
                        </span>
                        <span className="mt-1 block break-all text-[12px] text-muted">{citation.source_url}</span>
                      </a>
                    ))}
                    {askResponse.source_links.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
                        현재 권한으로 확인 가능한 답변 근거가 없습니다.
                      </div>
                    ) : null}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-8 text-[13px] text-muted">
                질문을 입력하면 AI 답변과 근거가 여기에 표시됩니다.
              </div>
            )}
          </div>
        </article>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
              <h2 className="text-[15px] font-extrabold">검색 근거</h2>
            </div>
            <span className="text-[12px] text-muted">
              {searchResponse ? `${searchResponse.results.length}개` : "대기 중"}
            </span>
          </div>

          {searchResponse?.results.map((result, resultIndex) => (
            <article key={`${result.id}-${result.source_id ?? resultIndex}`} className="panel reference-panel">
              <div className="flex flex-wrap items-center gap-2">
                <span className="badge blue">{result.source_type ?? "source"}</span>
                <span className="badge green">{result.permission_level}</span>
                <span className="badge violet">score {result.relevance_score.toFixed(2)}</span>
                {result.parser_status === "metadata_only" && (
                  <span className="badge amber" title={result.parser_status_reason || "메타데이터만 수집되었습니다"}>
                    메타데이터 반환 (본문 없음)
                  </span>
                )}
                {result.parser_status === "unsupported" && (
                  <span className="badge red" title={result.parser_status_reason || "지원되지 않는 파일 형식입니다."}>
                    미지원 파일 (본문 제외됨)
                  </span>
                )}
              </div>
              {result.matched_terms.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {result.matched_terms.map((term, termIndex) => (
                    <span key={`${term}-${termIndex}`} className="filter-pill active">{term}</span>
                  ))}
                </div>
              ) : null}
              <p className="mt-3 text-[13px] leading-6">{result.text}</p>
              <p className="mt-3 border-l-2 border-line pl-3 text-[13px] leading-6 text-muted">{result.source_snippet}</p>
              {result.source_url ? (
                <a href={result.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-[13px] font-bold text-[var(--primary-dark)] underline-offset-4 hover:underline">
                  <FileText className="h-4 w-4" aria-hidden="true" />
                  원문 열기
                </a>
              ) : null}
            </article>
          ))}

          {searchResponse && searchResponse.results.length === 0 ? (
            <div className="panel reference-panel p-8 text-[13px] text-muted">보여줄 수 있는 검색 결과가 없습니다.</div>
          ) : null}
        </section>
      </section>
    </div>
  );
}

function SearchPageFallback() {
  return <div className="panel reference-panel p-8 text-[13px] text-muted">검색 화면을 준비하고 있습니다.</div>;
}

type MetricIcon = typeof FileText;

function MetricCard({ icon: Icon, label, value }: { icon: MetricIcon; label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-soft p-3">
      <div className="flex items-center gap-2 text-[12px] text-muted">
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </div>
      <p className="mt-1 break-words text-[13px] font-extrabold">{value}</p>
    </div>
  );
}

function MemoryFreshnessPanel({ summary }: { summary?: RagIndexingSummaryResponse }) {
  const latestJob = summary?.latest_jobs[0];
  const indexedCount = summary?.state_counts.indexed ?? 0;
  const state = getFreshnessState(latestJob, indexedCount);
  const Icon = state.icon;
  const costPolicy = summary?.cost_policy;

  return (
    <section className={`rounded-lg border p-4 shadow-sm ${state.tone}`}>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <h2 className="text-[14px] font-extrabold">{state.title}</h2>
            <p className="mt-1 text-[13px] opacity-85">{state.description}</p>
          </div>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-white/70 px-3 py-2 text-[12px] font-bold">
          <Database className="h-4 w-4" aria-hidden="true" />
          {indexedCount.toLocaleString()}개 기억 사용 가능
        </span>
      </div>
      {costPolicy ? (
        <div className="mt-3 flex flex-wrap gap-2 text-[12px]">
          <span className="inline-flex items-center gap-2 rounded-lg bg-white/70 px-3 py-2 font-bold">
            <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
            예산{" "}
            {costPolicy.max_estimated_embedding_cost_usd === null || costPolicy.max_estimated_embedding_cost_usd === undefined
              ? "unlimited"
              : `$${costPolicy.max_estimated_embedding_cost_usd.toFixed(3)}`}
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg bg-white/70 px-3 py-2 font-bold">
            {costPolicy.embedding_model} · ${costPolicy.embedding_input_cost_per_1m_tokens.toFixed(2)}/1M tokens
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg bg-white/70 px-3 py-2 font-bold">
            {costPolicy.incremental_hash_skip ? "Hash skip active" : "Hash skip check"}
          </span>
        </div>
      ) : null}
    </section>
  );
}

function getFreshnessState(job: RagIndexingJobSummary | undefined, indexedCount: number) {
  if (!job) {
    return {
      title: "회사 메모리 준비 전",
      description: "아직 인덱싱 기록이 없습니다. 먼저 Slack, 메일, 문서를 동기화해 주세요.",
      tone: "border-[var(--line-soft)] bg-[var(--glass-elevated)] text-[var(--ink)]",
      icon: Clock3,
    };
  }
  if (job.status === "failed") {
    return {
      title: "회사 메모리 업데이트 확인 필요",
      description: "최근 인덱싱 작업이 실패했습니다. 기존 기억은 계속 검색할 수 있지만 운영 확인이 필요합니다.",
      tone: "border-red-200 bg-red-50 text-red-900",
      icon: ShieldAlert,
    };
  }
  if (job.status === "queued" || job.status === "running") {
    return {
      title: "회사 메모리 업데이트 중",
      description: "새 업무 기록을 반영하고 있습니다. 현재 검색은 마지막 완료된 기억을 기준으로 답변합니다.",
      tone: "border-blue-200 bg-blue-50 text-blue-900",
      icon: Clock3,
    };
  }
  if (indexedCount === 0) {
    return {
      title: "검색 가능한 회사 메모리가 없습니다",
      description: "권한으로 볼 수 있는 승인 기록이 아직 없습니다. 리뷰 승인 후 다시 검색해 주세요.",
      tone: "border-amber-200 bg-amber-50 text-amber-900",
      icon: ShieldAlert,
    };
  }
  return {
    title: "회사 메모리가 최신 상태입니다",
    description: `최근 업데이트: ${formatDateTime(job.updated_at)}. 승인된 기록을 기준으로 답변합니다.`,
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: CheckCircle2,
  };
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
