import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bot,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Database,
  Gauge,
  Loader2,
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
  OrchestrationStatusResponse,
  RagIndexingJobSummary,
  RagIndexingSummaryResponse,
} from "@/lib/api/types";
import { OrchestrationDryRun } from "./OrchestrationDryRun";

export const dynamic = "force-dynamic";

const STATUS_META: Record<
  string,
  {
    label: string;
    description: string;
    tone: string;
    icon: typeof CheckCircle2;
  }
> = {
  queued: {
    label: "대기 중",
    description: "Redis/Celery worker가 처리할 차례를 기다리고 있습니다.",
    tone: "border-amber-200 bg-amber-50 text-amber-900",
    icon: Clock3,
  },
  running: {
    label: "실행 중",
    description: "변경된 문서만 선별해 인덱싱하고 있습니다.",
    tone: "border-blue-200 bg-blue-50 text-blue-900",
    icon: Loader2,
  },
  complete: {
    label: "완료",
    description: "회사 메모리 인덱스가 최신 작업 결과를 반영했습니다.",
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: CheckCircle2,
  },
  failed: {
    label: "실패",
    description: "작업이 중단되었습니다. 실패 사유를 확인한 뒤 재실행이 필요합니다.",
    tone: "border-red-200 bg-red-50 text-red-900",
    icon: AlertTriangle,
  },
};

export default async function AgentRunsPage() {
  const [runs, summary, ragIndexing, orchestration] = await Promise.all([
    apiGet<AgentRunsResponse>("/api/v1/agent-runs"),
    apiGet<AgentRunSummaryResponse>("/api/v1/agent-runs/summary"),
    apiGet<RagIndexingSummaryResponse>("/api/v1/rag/indexing/summary"),
    apiGet<OrchestrationStatusResponse>("/api/v1/orchestration/company-memory"),
  ]);
  const cacheHitPercent = (summary.totals.cache_hit_rate * 100).toFixed(1);
  const latestRagJob = ragIndexing.latest_jobs[0];
  const jobStatusCounts = countJobStatuses(ragIndexing.latest_jobs);

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Agent Operations</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">AI 실행 관측</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            에이전트 실행 비용, 토큰 사용량, 캐시 적중률, RAG 인덱싱 상태를 운영자 관점에서 확인합니다.
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
          detail="AgentRun records"
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

      <OrchestrationStatusCard orchestration={orchestration} />

      <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-3 border-b border-[var(--line-soft)] px-4 py-4 lg:flex-row lg:items-center">
          <div>
            <h3 className="text-sm font-semibold">RAG 인덱싱 운영 상태</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              검색 사용자에게는 단순한 최신성만 보여주고, 인덱싱 비용과 처리 상태는 이 운영 화면에서 관리합니다.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-[#f4f8f6] px-3 py-2 text-xs font-semibold text-[#22513f]">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Admin observability
          </span>
        </div>
        <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,440px)]">
          <div className="space-y-4">
            <LatestIndexingJob job={latestRagJob} />
            <div className="grid gap-3 sm:grid-cols-3">
              <IndexingMetric
                icon={Database}
                label="Indexed"
                value={(ragIndexing.state_counts.indexed ?? 0).toLocaleString()}
                detail="serving vector states"
              />
              <IndexingMetric
                icon={RefreshCw}
                label="Skipped"
                value={(latestRagJob?.skipped_count ?? 0).toLocaleString()}
                detail="unchanged documents"
              />
              <IndexingMetric
                icon={CircleDollarSign}
                label="Saved Calls"
                value={(latestRagJob?.saved_embedding_calls ?? 0).toLocaleString()}
                detail="embedding calls avoided"
              />
            </div>
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 xl:grid-cols-2">
              {["queued", "running", "complete", "failed"].map((status) => (
                <StatusCount key={status} status={status} count={jobStatusCounts[status] ?? 0} />
              ))}
            </div>
            <RecentIndexingJobs jobs={ragIndexing.latest_jobs} />
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <h3 className="text-sm font-semibold">Agent별 비용과 토큰</h3>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              비용 합계 기준으로 정렬합니다. 최신 실행은 상세 감사 화면으로 바로 이동할 수 있습니다.
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

function OrchestrationStatusCard({ orchestration }: { orchestration: OrchestrationStatusResponse }) {
  const perRunBudgetUsd = orchestration.cost_policy.per_run_budget_usd ?? 0;
  const budgetActions = orchestration.cost_policy.budget_actions ?? ["run", "skip", "use_cache"];
  const costPolicyItems = [
    { label: "Delta sync", enabled: orchestration.cost_policy.delta_sync },
    { label: "Hash skip", enabled: orchestration.cost_policy.source_hash_skip },
    { label: "Evidence budget", enabled: orchestration.cost_policy.evidence_token_budget },
    {
      label: "Status API paid calls",
      enabled: orchestration.cost_policy.paid_llm_calls_in_status_api,
      inverted: true,
    },
  ];

  return (
    <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-lg bg-[#f4f8f6] px-3 py-2 text-xs font-semibold text-[#22513f]">
              <Bot className="h-4 w-4" aria-hidden="true" />
              LangGraph
            </span>
            <span className="rounded-lg border border-[var(--line-soft)] px-3 py-2 text-xs font-semibold text-[var(--ink-muted)]">
              {orchestration.backend}
            </span>
            <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900">
              dry-run cost $0
            </span>
            <span className="rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-xs font-semibold text-[var(--ink-muted)]">
              budget ${perRunBudgetUsd.toFixed(3)}/run
            </span>
          </div>
          <h3 className="mt-4 text-base font-semibold">Company Memory 오케스트레이터</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
            Slack, 메일/문서, 승인된 지식, RAG 답변을 하나의 그래프로 묶는 실행 순서입니다. 이 상태 조회는
            운영 확인용이라 모델 토큰을 쓰지 않습니다.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {orchestration.node_names.map((nodeName, index) => (
              <div key={nodeName} className="rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] px-3 py-2">
                <span className="text-[11px] font-semibold uppercase tracking-normal text-[var(--ink-muted)]">
                  Step {index + 1}
                </span>
                <p className="mt-1 text-xs font-semibold">{formatWorkflowNode(nodeName)}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] p-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            <h4 className="text-sm font-semibold">비용 가드레일</h4>
          </div>
          <div className="mt-3 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-xs">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-[var(--ink-muted)]">Per-run budget</span>
              <span className="font-semibold">${perRunBudgetUsd.toFixed(3)}</span>
            </div>
            <p className="mt-2 text-[var(--ink-muted)]">
              {budgetActions.join(" / ")} 정책으로 큰 입력과 캐시 히트를 분기합니다.
            </p>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
            {costPolicyItems.map((item) => {
              const isHealthy = item.inverted ? !item.enabled : item.enabled;
              return (
                <div
                  key={item.label}
                  className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-xs"
                >
                  <span className="font-medium text-[var(--ink-muted)]">{item.label}</span>
                  <span
                    className={`rounded-md px-2 py-1 font-semibold ${
                      isHealthy ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"
                    }`}
                  >
                    {item.inverted && isHealthy ? "blocked" : isHealthy ? "active" : "check"}
                  </span>
                </div>
              );
            })}
          </div>
          <OrchestrationDryRun />
        </div>
      </div>
    </section>
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

  const meta = getStatusMeta(job.status);
  const Icon = meta.icon;

  return (
    <div className={`rounded-lg border px-4 py-4 ${meta.tone}`}>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <p className="text-sm font-semibold">최근 인덱싱 작업: {meta.label}</p>
          </div>
          <p className="mt-1 text-xs opacity-80">{meta.description}</p>
          <p className="mt-2 break-all text-xs opacity-80">{job.job_id}</p>
        </div>
        <span className="inline-flex w-fit items-center rounded-lg border border-current px-2 py-1 text-xs font-semibold">
          {job.progress_pct}%
        </span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/70">
        <div className="h-full rounded-full bg-current" style={{ width: `${clampPercent(job.progress_pct)}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <JobCounter label="indexed" value={job.indexed_count} />
        <JobCounter label="skipped" value={job.skipped_count} />
        <JobCounter label="saved" value={job.saved_embedding_calls} />
      </div>
      {job.failure_reason ? (
        <div className="mt-3 rounded-lg border border-current bg-white/60 p-3 text-xs">
          <p className="font-semibold">실패 사유</p>
          <p className="mt-1">{job.failure_reason}</p>
        </div>
      ) : null}
      <p className="mt-3 text-xs opacity-75">마지막 업데이트: {formatDateTime(job.updated_at)}</p>
    </div>
  );
}

function RecentIndexingJobs({ jobs }: { jobs: RagIndexingJobSummary[] }) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-white">
      <div className="border-b border-[var(--line-soft)] px-3 py-3">
        <h4 className="text-sm font-semibold">최근 RAG 작업</h4>
      </div>
      <div className="divide-y divide-[var(--line-soft)]">
        {jobs.map((job) => {
          const meta = getStatusMeta(job.status);
          return (
            <div key={job.job_id} className="px-3 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="min-w-0 truncate text-xs font-semibold">{job.job_id}</p>
                <span className={`shrink-0 rounded-md border px-2 py-1 text-xs font-semibold ${meta.tone}`}>
                  {meta.label}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--ink-muted)]">
                indexed {job.indexed_count.toLocaleString()} · skipped {job.skipped_count.toLocaleString()} · saved{" "}
                {job.saved_embedding_calls.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-[var(--ink-muted)]">{formatDateTime(job.updated_at)}</p>
            </div>
          );
        })}
        {jobs.length === 0 ? (
          <p className="px-3 py-6 text-sm text-[var(--ink-muted)]">표시할 RAG 작업이 없습니다.</p>
        ) : null}
      </div>
    </div>
  );
}

function StatusCount({ status, count }: { status: string; count: number }) {
  const meta = getStatusMeta(status);
  const Icon = meta.icon;
  return (
    <div className={`rounded-lg border px-3 py-2 ${meta.tone}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1 font-semibold">
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          {meta.label}
        </span>
        <span>{count.toLocaleString()}</span>
      </div>
    </div>
  );
}

function JobCounter({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-white/60 px-2 py-2">
      <p className="font-semibold">{value.toLocaleString()}</p>
      <p className="mt-0.5 opacity-75">{label}</p>
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

function getStatusMeta(status: string) {
  return STATUS_META[status] ?? {
    label: status,
    description: "알 수 없는 작업 상태입니다.",
    tone: "border-neutral-200 bg-neutral-50 text-neutral-800",
    icon: Activity,
  };
}

function countJobStatuses(jobs: RagIndexingJobSummary[]) {
  return jobs.reduce<Record<string, number>>((counts, job) => {
    counts[job.status] = (counts[job.status] ?? 0) + 1;
    return counts;
  }, {});
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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

function formatWorkflowNode(nodeName: string) {
  const labels: Record<string, string> = {
    collect_evidence: "Evidence 수집",
    draft_review_candidates: "Review 후보",
    retrieve_company_memory: "Memory 검색",
    answer_with_rag: "RAG 답변",
  };
  return labels[nodeName] ?? nodeName;
}
