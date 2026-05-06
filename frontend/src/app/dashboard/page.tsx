import { ArrowRight, Bot, CircleDollarSign, Database, ShieldAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { serverApiGet } from "@/lib/api/server";
import type { AgentRunsResponse, DashboardResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const EMPTY_AGENT_RUNS: AgentRunsResponse = {
  total_runs: 0,
  total_tokens: 0,
  estimated_cost_usd: 0,
  recent_runs: [],
};

export default async function DashboardPage() {
  const [dashboard, agentRuns] = await Promise.all([
    serverApiGet<DashboardResponse>("/api/v1/dashboard"),
    serverApiGet<AgentRunsResponse>("/api/v1/agent-runs").catch(() => EMPTY_AGENT_RUNS),
  ]);
  const totalSources = Object.values(dashboard.source_counts).reduce((sum, count) => sum + count, 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Workspace Overview</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">오늘의 업무 흐름</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            수집된 출처, 검토 대기열, 동기화 작업, AI Agent 비용 흐름을 한곳에서 확인합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <Sparkles className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          Agent cost audit
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard icon={Database} label="수집 출처" value={totalSources.toLocaleString()} />
        <MetricCard
          icon={ShieldAlert}
          label="검토 대기"
          value={dashboard.pending_review_count.toLocaleString()}
        />
        <MetricCard icon={Bot} label="Agent 실행" value={agentRuns.total_runs.toLocaleString()} />
        <MetricCard
          icon={CircleDollarSign}
          label="예상 비용"
          value={`$${agentRuns.estimated_cost_usd.toFixed(6)}`}
          detail={`${agentRuns.total_tokens.toLocaleString()} tokens`}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-3">
            <h3 className="text-sm font-semibold">최근 동기화 작업</h3>
          </div>
          <div className="divide-y divide-[var(--line-soft)]">
            {dashboard.recent_jobs.map((job) => (
              <div key={job.job_id} className="grid gap-3 px-4 py-3 sm:grid-cols-[1fr_110px_90px]">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{job.job_id}</p>
                  <p className="text-sm text-[var(--ink-muted)]">{job.message}</p>
                </div>
                <span className="text-sm capitalize text-[var(--ink-muted)]">{job.connector_type}</span>
                <span className="text-sm font-medium capitalize">{job.status}</span>
              </div>
            ))}
            {dashboard.recent_jobs.length === 0 ? (
              <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">
                아직 실행된 동기화 작업이 없습니다.
              </p>
            ) : null}
          </div>
        </div>

        <div className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-3">
            <h3 className="text-sm font-semibold">유형별 출처</h3>
          </div>
          <div className="divide-y divide-[var(--line-soft)]">
            {Object.entries(dashboard.source_counts).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between px-4 py-3">
                <span className="text-sm font-medium capitalize">{type}</span>
                <span className="text-sm text-[var(--ink-muted)]">{count}</span>
              </div>
            ))}
            {Object.keys(dashboard.source_counts).length === 0 ? (
              <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">아직 승인된 출처가 없습니다.</p>
            ) : null}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-2 border-b border-[var(--line-soft)] px-4 py-3 sm:flex-row sm:items-center">
          <div>
            <h3 className="text-sm font-semibold">최근 Agent 실행</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              프롬프트 버전, 토큰, 비용, 권한 범위를 함께 추적합니다.
            </p>
          </div>
          <Link
            href="/agent-runs"
            className="inline-flex items-center gap-1 rounded-full bg-[#ecfbf6] px-2.5 py-1 text-xs font-semibold text-[#0f6f58]"
          >
            전체 보기
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
        <div className="divide-y divide-[var(--line-soft)]">
          {agentRuns.recent_runs.map((run) => (
            <Link
              key={run.id}
              href={`/agent-runs/${run.id}`}
              className="grid gap-3 px-4 py-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(180px,0.8fr)_120px_120px]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{formatAgentName(run.agent_name)}</p>
                <p className="mt-1 truncate text-xs text-[var(--ink-muted)]">{run.prompt_version}</p>
              </div>
              <div className="min-w-0 text-xs text-[var(--ink-muted)]">
                <p className="truncate">{run.source_window}</p>
                <p className="mt-1 truncate">{run.model_name}</p>
              </div>
              <div className="text-sm">
                <p className="font-semibold">{run.total_tokens.toLocaleString()}</p>
                <p className="text-xs text-[var(--ink-muted)]">tokens</p>
              </div>
              <div className="text-sm">
                <p className="font-semibold">${run.estimated_cost_usd.toFixed(6)}</p>
                <p className="text-xs capitalize text-[var(--ink-muted)]">{run.permission_level}</p>
              </div>
            </Link>
          ))}
          {agentRuns.recent_runs.length === 0 ? (
            <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">
              아직 실행된 Agent가 없습니다. Integrations 또는 Company Memory에서 Agent를 실행해보세요.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}

type MetricIcon = typeof Database;

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: MetricIcon;
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--ink-muted)]">{label}</span>
        <Icon className="h-4 w-4 text-[var(--ink-muted)]" aria-hidden="true" />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
      {detail ? <p className="mt-1 text-xs text-[var(--ink-muted)]">{detail}</p> : null}
    </div>
  );
}

function formatAgentName(agentName: string) {
  if (agentName === "slack_agent") {
    return "Slack Agent";
  }
  if (agentName === "mail_document_agent") {
    return "Mail/Docs Agent";
  }
  if (agentName === "rag_orchestrator_agent") {
    return "RAG Orchestrator";
  }
  return agentName;
}
