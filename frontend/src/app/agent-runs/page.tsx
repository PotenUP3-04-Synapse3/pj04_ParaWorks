import {
  Activity,
  ArrowRight,
  BarChart3,
  Bot,
  CircleDollarSign,
  Database,
  Gauge,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { apiGet } from "@/lib/api/client";
import type {
  AgentRunAgentSummary,
  AgentRunsResponse,
  AgentRunSummaryResponse,
  RagIndexingJobSummary,
  RagIndexingSummaryResponse,
} from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function AgentRunsPage() {
  const [runs, summary, ragIndexing] = await Promise.all([
    apiGet<AgentRunsResponse>("/api/v1/agent-runs"),
    apiGet<AgentRunSummaryResponse>("/api/v1/agent-runs/summary"),
    apiGet<RagIndexingSummaryResponse>("/api/v1/rag/indexing/summary"),
  ]);
  const cacheHitPercent = (summary.totals.cache_hit_rate * 100).toFixed(1);
  const latestRagJob = ragIndexing.latest_jobs[0];

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Agent Operations</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">AI 실행 관측</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            멀티에이전트 실행 비용, 토큰 사용량, 캐시 적중률, Agent별 상태를 한 화면에서 확인합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <BarChart3 className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {summary.totals.total_runs} audited runs
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Bot}
          label="총 실행"
          value={summary.totals.total_runs.toLocaleString()}
          detail="AgentRun rows"
        />
        <MetricCard
          icon={Sparkles}
          label="총 토큰"
          value={summary.totals.total_tokens.toLocaleString()}
          detail={`${summary.totals.average_tokens_per_run.toLocaleString()} avg/run`}
        />
        <MetricCard
          icon={CircleDollarSign}
          label="예상 비용"
          value={`$${summary.totals.estimated_cost_usd.toFixed(6)}`}
          detail={`$${summary.totals.average_cost_per_run.toFixed(6)} avg/run`}
        />
        <MetricCard
          icon={Gauge}
          label="캐시 적중"
          value={`${cacheHitPercent}%`}
          detail={`${summary.totals.cache_hits.toLocaleString()} cached runs`}
        />
      </section>

      <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-3 border-b border-[var(--line-soft)] px-4 py-4 lg:flex-row lg:items-center">
          <div>
            <h3 className="text-sm font-semibold">RAG 인덱싱 운영 상태</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              운영자용 지표입니다. 검색 화면에는 노출하지 않고 인덱싱 비용 절감과 처리 상태만 관측합니다.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-[#f4f8f6] px-3 py-2 text-xs font-semibold text-[#22513f]">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Admin observability
          </span>
        </div>
        <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
          <div className="grid gap-3 sm:grid-cols-3">
            <IndexingMetric
              icon={Database}
              label="Indexed"
              value={(ragIndexing.state_counts.indexed ?? 0).toLocaleString()}
              detail="served vector states"
            />
            <IndexingMetric
              icon={RefreshCw}
              label="Skipped"
              value={(latestRagJob?.skipped_count ?? 0).toLocaleString()}
              detail="unchanged docs"
            />
            <IndexingMetric
              icon={CircleDollarSign}
              label="Saved Calls"
              value={(latestRagJob?.saved_embedding_calls ?? 0).toLocaleString()}
              detail="embedding calls avoided"
            />
          </div>
          <LatestIndexingJob job={latestRagJob} />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <h3 className="text-sm font-semibold">Agent별 비용과 토큰</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              비용 합계 기준으로 정렬합니다. 최신 실행은 상세 화면으로 바로 이동합니다.
            </p>
          </div>
          <div className="divide-y divide-[var(--line-soft)]">
            {summary.by_agent.map((agent) => (
              <AgentSummaryRow key={agent.agent_name} agent={agent} />
            ))}
            {summary.by_agent.length === 0 ? (
              <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">
                아직 기록된 Agent 실행이 없습니다.
              </p>
            ) : null}
          </div>
        </article>

        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <h3 className="text-sm font-semibold">상태 분포</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">완료, 실패, 진행 상태를 집계합니다.</p>
          </div>
          <div className="space-y-3 p-4">
            {Object.entries(summary.by_status).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between rounded-lg bg-[#fbfaf8] px-3 py-2">
                <span className="inline-flex items-center gap-2 text-sm font-medium capitalize">
                  <Activity className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
                  {status}
                </span>
                <span className="text-sm font-semibold">{count.toLocaleString()}</span>
              </div>
            ))}
            {Object.keys(summary.by_status).length === 0 ? (
              <p className="py-4 text-sm text-[var(--ink-muted)]">아직 상태 데이터가 없습니다.</p>
            ) : null}
          </div>
        </article>
      </section>

      <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
        <div className="border-b border-[var(--line-soft)] px-4 py-4">
          <h3 className="text-sm font-semibold">최근 실행 로그</h3>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            프롬프트, 모델, 권한, 비용을 확인하고 상세 감사 화면으로 이동합니다.
          </p>
        </div>
        <div className="divide-y divide-[var(--line-soft)]">
          {runs.recent_runs.map((run) => (
            <Link
              key={run.id}
              href={`/agent-runs/${run.id}`}
              className="grid gap-3 px-4 py-3 transition hover:bg-[#fbfaf8] lg:grid-cols-[minmax(0,1.2fr)_minmax(220px,1fr)_120px_120px_80px]"
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
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#21132b]">
                상세
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            </Link>
          ))}
          {runs.recent_runs.length === 0 ? (
            <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">
              아직 실행된 Agent가 없습니다. Integrations 또는 Company Memory에서 Agent를 실행해보세요.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}

type MetricIcon = typeof Bot;

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: MetricIcon;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--ink-muted)]">{label}</span>
        <Icon className="h-4 w-4 text-[var(--ink-muted)]" aria-hidden="true" />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-[var(--ink-muted)]">{detail}</p>
    </div>
  );
}

function IndexingMetric({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: MetricIcon;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-[var(--ink-muted)]">{label}</span>
        <Icon className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
      </div>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-[var(--ink-muted)]">{detail}</p>
    </div>
  );
}

function LatestIndexingJob({ job }: { job?: RagIndexingJobSummary }) {
  if (!job) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--line-soft)] px-4 py-5 text-sm text-[var(--ink-muted)]">
        아직 실행된 RAG 인덱싱 작업이 없습니다.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--line-soft)] px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{job.job_id}</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">{job.message}</p>
        </div>
        <span className="rounded-lg bg-[#f4f8f6] px-2 py-1 text-xs font-semibold capitalize text-[#22513f]">
          {job.status}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <JobCounter label="indexed" value={job.indexed_count} />
        <JobCounter label="skipped" value={job.skipped_count} />
        <JobCounter label="saved" value={job.saved_embedding_calls} />
      </div>
    </div>
  );
}

function JobCounter({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-[#fbfaf8] px-2 py-2">
      <p className="font-semibold">{value.toLocaleString()}</p>
      <p className="mt-0.5 text-[var(--ink-muted)]">{label}</p>
    </div>
  );
}

function AgentSummaryRow({ agent }: { agent: AgentRunAgentSummary }) {
  return (
    <div className="grid gap-3 px-4 py-4 lg:grid-cols-[minmax(0,1fr)_120px_120px_120px_120px]">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">{formatAgentName(agent.agent_name)}</p>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">
          {agent.run_count.toLocaleString()} runs · latest {agent.latest_status}
        </p>
      </div>
      <div className="text-sm">
        <p className="font-semibold">{agent.total_tokens.toLocaleString()}</p>
        <p className="text-xs text-[var(--ink-muted)]">tokens</p>
      </div>
      <div className="text-sm">
        <p className="font-semibold">{agent.average_tokens_per_run.toLocaleString()}</p>
        <p className="text-xs text-[var(--ink-muted)]">avg/run</p>
      </div>
      <div className="text-sm">
        <p className="font-semibold">${agent.estimated_cost_usd.toFixed(6)}</p>
        <p className="text-xs text-[var(--ink-muted)]">cost</p>
      </div>
      <Link
        href={`/agent-runs/${agent.latest_run_id}`}
        className="inline-flex items-center gap-1 text-sm font-semibold text-[#21132b] underline-offset-4 hover:underline"
      >
        최신 상세
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </Link>
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
