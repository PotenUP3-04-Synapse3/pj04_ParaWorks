"use client";

import {
  Bot,
  CircleDollarSign,
  FileText,
  Link2,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiPost } from "@/lib/api/client";
import type { AskResponse, SearchResponse } from "@/lib/api/types";

const DEFAULT_QUESTION = "Redis job state";

export default function SearchPage() {
  const [query, setQuery] = useState(DEFAULT_QUESTION);
  const [searchResponse, setSearchResponse] = useState<SearchResponse>();
  const [askResponse, setAskResponse] = useState<AskResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const runMemoryQuery = useCallback(async (nextQuery: string) => {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) {
      return;
    }

    setLoading(true);
    setError(undefined);

    try {
      const [askResult, searchResult] = await Promise.all([
        apiPost<AskResponse>("/api/v1/ask", { question: trimmedQuery }, "viewer"),
        apiPost<SearchResponse>("/api/v1/search", { query: trimmedQuery }, "viewer"),
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
    void runMemoryQuery(DEFAULT_QUESTION);
  }, [runMemoryQuery]);

  const permissionNotice = askResponse?.permission_notice ?? searchResponse?.permission_notice;

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Company Memory</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">회사 메모리에 질문하기</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            viewer 권한으로 답변과 검색 근거를 함께 확인합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          RAG Orchestrator
        </div>
      </div>

      <form onSubmit={submit} className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
        <label htmlFor="query" className="text-sm font-semibold">
          질문
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="h-11 min-w-0 flex-1 rounded-lg border border-[var(--line-soft)] bg-white px-3 text-sm outline-none focus:border-[var(--workspace-rail-active)]"
            placeholder="예: Redis는 무엇에 쓰이나요?"
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-neutral-300 disabled:bg-neutral-300"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {loading ? "질문 중" : "AI에게 질문"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      ) : null}

      {permissionNotice ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">권한으로 숨겨진 근거가 있습니다.</p>
            <p className="mt-1 text-amber-800">{permissionNotice}</p>
          </div>
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]">
        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-[var(--workspace-rail-active)]" aria-hidden="true" />
              <h3 className="text-sm font-semibold">AI 답변</h3>
            </div>
          </div>

          <div className="space-y-4 p-4">
            {askResponse ? (
              <>
                <p className="text-base leading-7">{askResponse.answer}</p>

                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricCard
                    icon={CircleDollarSign}
                    label="예상 비용"
                    value={`$${askResponse.estimated_cost_usd.toFixed(6)}`}
                  />
                  <MetricCard
                    icon={Sparkles}
                    label="토큰"
                    value={askResponse.token_usage.total_tokens.toLocaleString()}
                  />
                  <MetricCard
                    icon={ShieldAlert}
                    label="숨김 근거"
                    value={askResponse.hidden_match_count.toString()}
                  />
                </div>

                <div className="rounded-lg bg-[#fbfaf8] p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                    Agent metadata
                  </p>
                  <dl className="mt-2 grid gap-2 text-xs text-[var(--ink-muted)] sm:grid-cols-2">
                    <MetaRow label="Agent" value={formatAgentName(askResponse.agent_name)} />
                    <MetaRow label="Prompt" value={askResponse.prompt_version} />
                    <MetaRow label="Model" value={askResponse.model_name} />
                    <MetaRow label="Permission" value={askResponse.permission_level} />
                  </dl>
                  <p className="mt-2 break-all text-xs text-[var(--ink-muted)]">
                    cache: {askResponse.cache_key}
                  </p>
                </div>

                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                    <Link2 className="h-4 w-4" aria-hidden="true" />
                    답변 근거
                  </div>
                  <div className="space-y-2">
                    {askResponse.source_links.map((sourceLink, index) => (
                      <a
                        key={`${sourceLink}-${index}`}
                        href={sourceLink}
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded-lg border border-[var(--line-soft)] bg-white p-3 text-sm hover:bg-[#fbfaf8]"
                      >
                        <span className="font-medium text-[#21132b]">근거 {index + 1}</span>
                        <span className="mt-1 block break-all text-xs text-[var(--ink-muted)]">{sourceLink}</span>
                      </a>
                    ))}
                    {askResponse.source_links.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-[var(--line-soft)] bg-[#fbfaf8] p-4 text-sm text-[var(--ink-muted)]">
                        현재 권한으로 확인 가능한 답변 근거가 없습니다.
                      </div>
                    ) : null}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-[var(--line-soft)] bg-[#fbfaf8] p-8 text-sm text-[var(--ink-muted)]">
                질문을 입력하면 AI 답변과 근거가 여기에 표시됩니다.
              </div>
            )}
          </div>
        </article>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-[var(--workspace-rail-active)]" aria-hidden="true" />
              <h3 className="text-sm font-semibold">검색 근거</h3>
            </div>
            <span className="text-xs text-[var(--ink-muted)]">
              {searchResponse ? `${searchResponse.results.length}개` : "대기 중"}
            </span>
          </div>

          {searchResponse?.results.map((result) => (
            <article key={result.id} className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-[var(--line-soft)] px-2 py-1 text-xs font-medium capitalize text-[var(--ink-muted)]">
                  {result.source_type ?? "source"}
                </span>
                <span className="rounded-md border border-[var(--line-soft)] px-2 py-1 text-xs font-medium capitalize text-[var(--ink-muted)]">
                  {result.permission_level}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6">{result.text}</p>
              <p className="mt-3 border-l-2 border-[var(--line-soft)] pl-3 text-sm leading-6 text-[var(--ink-muted)]">
                {result.source_snippet}
              </p>
              {result.source_url ? (
                <a
                  href={result.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[#21132b] underline-offset-4 hover:underline"
                >
                  <FileText className="h-4 w-4" aria-hidden="true" />
                  원문 열기
                </a>
              ) : null}
            </article>
          ))}

          {searchResponse && searchResponse.results.length === 0 ? (
            <div className="rounded-lg border border-dashed border-[var(--line-soft)] bg-white p-8 text-sm text-[var(--ink-muted)]">
              볼 수 있는 검색 결과가 없습니다.
            </div>
          ) : null}
        </section>
      </section>
    </div>
  );
}

type MetricIcon = typeof CircleDollarSign;

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: MetricIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg bg-[#fbfaf8] p-3">
      <div className="flex items-center gap-2 text-xs text-[var(--ink-muted)]">
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </div>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="font-semibold text-[var(--ink-strong)]">{label}</dt>
      <dd className="mt-0.5 truncate">{value}</dd>
    </div>
  );
}

function formatAgentName(agentName: string) {
  if (agentName === "rag_orchestrator_agent") {
    return "RAG Orchestrator";
  }
  return agentName;
}
