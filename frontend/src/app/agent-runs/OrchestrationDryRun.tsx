"use client";

import { CheckCircle2, Loader2, Play, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { apiPost } from "@/lib/api/client";
import type { OrchestrationDryRunResponse } from "@/lib/api/types";

const DRY_RUN_QUESTION = "Redis queue state";

export function OrchestrationDryRun() {
  const [result, setResult] = useState<OrchestrationDryRunResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  async function runDryRun() {
    setIsRunning(true);
    setErrorMessage(null);
    try {
      const response = await apiPost<OrchestrationDryRunResponse>(
        "/api/v1/orchestration/company-memory/dry-run",
        {
          objective: "answer_from_company_memory",
          question: DRY_RUN_QUESTION,
        },
      );
      setResult(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Dry-run 실행에 실패했습니다.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="mt-4 rounded-lg border border-[var(--line-soft)] bg-white p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold">Zero-cost dry-run</p>
          <p className="mt-1 text-xs leading-5 text-[var(--ink-muted)]">
            실제 Slack, embedding, LLM 호출 없이 LangGraph 실행 경로만 확인합니다.
          </p>
        </div>
        <button
          type="button"
          onClick={runDryRun}
          disabled={isRunning}
          className="inline-flex w-fit items-center gap-2 whitespace-nowrap rounded-lg bg-[#21132b] px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#3a214b] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
          Dry-run 실행
        </button>
      </div>

      {result ? (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 font-semibold">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Dry-run 완료
            </span>
            <span className="rounded-md bg-white/70 px-2 py-1 font-semibold">
              {result.completed_nodes.length}개 노드 실행
            </span>
            <span className="rounded-md bg-white/70 px-2 py-1 font-semibold">토큰 비용 ${result.token_cost_usd}</span>
          </div>
          <p className="mt-2 break-all font-medium">{result.outputs.token_budget_policy}</p>
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
