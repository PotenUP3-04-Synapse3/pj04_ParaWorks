"use client";

import { Search } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiPost } from "@/lib/api/client";
import type { SearchResponse } from "@/lib/api/types";

export default function SearchPage() {
  const [query, setQuery] = useState("Redis");
  const [response, setResponse] = useState<SearchResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const runSearch = useCallback(async (nextQuery: string) => {
    setLoading(true);
    setError(undefined);

    try {
      const result = await apiPost<SearchResponse>("/api/v1/search", { query: nextQuery }, "viewer");
      setResponse(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검색에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch(query);
  }

  useEffect(() => {
    void runSearch("Redis");
  }, [runSearch]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-muted">뷰어 권한</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">검색</h2>
      </div>

      <form onSubmit={submit} className="rounded-md border border-line bg-white p-4">
        <label htmlFor="query" className="text-sm font-medium">
          검색어
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="h-10 min-w-0 flex-1 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-neutral-500"
            placeholder="색인된 출처 내용을 검색하세요"
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-neutral-900 px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            <Search className="h-4 w-4" aria-hidden="true" />
            {loading ? "검색 중" : "검색"}
          </button>
        </div>
      </form>

      {response?.permission_notice ? (
        <div className="rounded-md border border-line bg-white p-4 text-sm text-muted">
          {response.permission_notice}
        </div>
      ) : null}
      {error ? <div className="rounded-md border border-red-200 bg-white p-4 text-sm text-red-700">{error}</div> : null}

      <section className="space-y-3">
        {response?.results.map((result) => (
          <article key={result.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                {result.source_type ?? "source"}
              </span>
              <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                {result.permission_level}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6">{result.text}</p>
            <p className="mt-3 border-l-2 border-line pl-3 text-sm leading-6 text-muted">
              {result.source_snippet}
            </p>
            {result.source_url ? (
              <a
                href={result.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-block text-sm font-medium text-neutral-700 underline-offset-4 hover:underline"
              >
                원문 열기
              </a>
            ) : null}
          </article>
        ))}
        {response && response.results.length === 0 ? (
          <div className="rounded-md border border-line bg-white p-8 text-sm text-muted">
            볼 수 있는 검색 결과가 없습니다.
          </div>
        ) : null}
      </section>
    </div>
  );
}
