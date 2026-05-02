"use client";

import { CheckCircle2, CircleDollarSign, Loader2, Play, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { apiPost } from "@/lib/api/client";
import type { RagIndexingSummaryResponse, RagReindexResponse } from "@/lib/api/types";

type RunResult = {
  job_id?: string;
  status?: string;
  dry_run?: boolean;
  indexed_count?: number;
  skipped_count?: number;
  saved_embedding_calls?: number;
};

export function RagReindexControl({ summary }: { summary: RagIndexingSummaryResponse }) {
  const [preview, setPreview] = useState<RagReindexResponse | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  async function runPreview() {
    setIsPreviewing(true);
    setErrorMessage(null);
    setRunResult(null);
    try {
      const response = await apiPost<RagReindexResponse>("/api/v1/rag/reindex?dry_run=true");
      setPreview(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "재색인 미리보기에 실패했습니다.");
    } finally {
      setIsPreviewing(false);
    }
  }

  async function runApprovedReindex() {
    setIsRunning(true);
    setErrorMessage(null);
    try {
      const response = await apiPost<RunResult>("/api/v1/rag/reindex/jobs?dry_run=false");
      setRunResult(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "실제 재색인 실행에 실패했습니다.");
    } finally {
      setIsRunning(false);
    }
  }

  const budget = preview?.embedding_budget;
  const latestJob = summary.latest_jobs[0];
  const canRun = Boolean(preview) && budget?.budget_status !== "over_budget";

  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] p-4" data-testid="rag-reindex-control">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            <h4 className="text-sm font-semibold">RAG 재색인 승인</h4>
          </div>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-[var(--ink-muted)]">
            먼저 dry-run으로 변경 문서와 예상 임베딩 비용을 확인한 뒤 실제 pgvector 재색인을 실행합니다.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={runPreview}
            disabled={isPreviewing || isRunning}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-xs font-semibold text-[var(--ink-strong)] shadow-sm transition hover:bg-white/80 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isPreviewing ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            )}
            비용 미리보기
          </button>
          <button
            type="button"
            onClick={runApprovedReindex}
            disabled={!canRun || isPreviewing || isRunning}
            className="inline-flex items-center gap-2 rounded-lg bg-[#21132b] px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#3a214b] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="h-4 w-4" aria-hidden="true" />
            )}
            승인 후 실행
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <ReindexStat label="현재 인덱스" value={(summary.state_counts.indexed ?? 0).toLocaleString()} />
        <ReindexStat label="최근 skipped" value={(latestJob?.skipped_count ?? 0).toLocaleString()} />
        <ReindexStat label="최근 saved" value={(latestJob?.saved_embedding_calls ?? 0).toLocaleString()} />
      </div>

      {budget ? (
        <div
          className={`mt-3 rounded-lg border p-3 text-xs ${
            budget.budget_status === "over_budget"
              ? "border-amber-200 bg-amber-50 text-amber-900"
              : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
          data-testid="rag-reindex-preview"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 font-semibold">
              {budget.budget_status === "over_budget" ? (
                <TriangleAlert className="h-4 w-4" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              )}
              {budget.budget_status === "over_budget" ? "예산 초과" : "실행 가능"}
            </span>
            <span className="rounded-md bg-white/70 px-2 py-1 font-semibold">
              변경 {budget.changed_document_count.toLocaleString()}개
            </span>
            <span className="rounded-md bg-white/70 px-2 py-1 font-semibold">
              예상 {budget.estimated_input_tokens.toLocaleString()} tokens
            </span>
            <span className="inline-flex items-center gap-1 rounded-md bg-white/70 px-2 py-1 font-semibold">
              <CircleDollarSign className="h-3.5 w-3.5" aria-hidden="true" />
              {formatUsd(budget.estimated_cost_usd)}
            </span>
          </div>
          <p className="mt-2 text-[var(--ink-muted)]">
            {budget.embedding_model} · 한도{" "}
            {budget.budget_limit_usd === null || budget.budget_limit_usd === undefined
              ? "없음"
              : formatUsd(budget.budget_limit_usd)}
            {budget.budget_status === "over_budget"
              ? " · 실제 실행은 설정된 비용 가드가 차단합니다."
              : " · 승인 후 실제 재색인을 실행할 수 있습니다."}
          </p>
        </div>
      ) : null}

      {runResult ? (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
          <p className="font-semibold">재색인 요청 완료</p>
          <p className="mt-1">
            {runResult.job_id ? `${runResult.job_id} · ` : ""}
            {runResult.status ?? "queued"}
          </p>
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-900">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>{errorMessage}</p>
        </div>
      ) : null}
    </div>
  );
}

function ReindexStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2">
      <p className="text-xs font-medium text-[var(--ink-muted)]">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatUsd(value: number) {
  return `$${value.toFixed(6)}`;
}
