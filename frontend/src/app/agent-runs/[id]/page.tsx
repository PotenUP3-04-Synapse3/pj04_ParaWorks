import { ArrowLeft, Bot, CircleDollarSign, Fingerprint, ShieldAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { apiGet } from "@/lib/api/client";
import type { AgentRunSummaryItem } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type AgentRunDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AgentRunDetailPage({ params }: AgentRunDetailPageProps) {
  const { id } = await params;
  let run: AgentRunSummaryItem;

  try {
    run = await apiGet<AgentRunSummaryItem>(`/api/v1/agent-runs/${id}`);
  } catch {
    return <AdminOnlyNotice />;
  }
  const tokenUsage = run.token_usage ?? {
    input_tokens: run.input_tokens,
    output_tokens: run.output_tokens,
    total_tokens: run.total_tokens,
  };
  const evidenceSummary = run.evidence_summary ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--workspace-rail-active)]"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            대시보드로 돌아가기
          </Link>
          <p className="mt-4 text-sm font-semibold text-[var(--workspace-rail-active)]">Agent Run</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">{formatAgentName(run.agent_name)}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            실행 {run.id}의 프롬프트, 모델, 비용, 토큰, 권한, 캐시 정보를 확인합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {run.status}
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard icon={Sparkles} label="Total tokens" value={tokenUsage.total_tokens.toLocaleString()} />
        <MetricCard icon={CircleDollarSign} label="Estimated cost" value={`$${run.estimated_cost_usd.toFixed(6)}`} />
        <MetricCard icon={ShieldAlert} label="Permission" value={run.permission_level} />
        <MetricCard icon={Fingerprint} label="Run ID" value={run.id.toString()} />
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <h3 className="text-sm font-semibold">실행 계약</h3>
          </div>
          <dl className="grid gap-4 p-4 sm:grid-cols-2">
            <Meta label="Agent" value={run.agent_name} />
            <Meta label="Prompt version" value={run.prompt_version} />
            <Meta label="Model" value={run.model_name} />
            <Meta label="Source window" value={run.source_window} />
            <Meta label="Selection" value={run.selection_strategy ?? "standard"} />
            <Meta label="Started" value={formatDate(run.started_at)} />
            <Meta label="Completed" value={run.completed_at ? formatDate(run.completed_at) : "not recorded"} />
          </dl>
          <div className="border-t border-[var(--line-soft)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">Cache key</p>
            <p className="mt-2 break-all rounded-lg bg-[#fbfaf8] p-3 text-xs text-[var(--ink-muted)]">
              {run.cache_key}
            </p>
          </div>
        </article>

        <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <h3 className="text-sm font-semibold">토큰 세부</h3>
          </div>
          <div className="space-y-3 p-4">
            <TokenRow label="Input" value={tokenUsage.input_tokens} />
            <TokenRow label="Output" value={tokenUsage.output_tokens} />
            <TokenRow label="Total" value={tokenUsage.total_tokens} />
          </div>
        </article>
      </section>

      {evidenceSummary.length ? (
        <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="flex flex-col gap-1 border-b border-[var(--line-soft)] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-sm font-semibold">Ranked evidence</h3>
            <p className="text-xs text-[var(--ink-muted)]">{evidenceSummary.length.toLocaleString()} selected messages</p>
          </div>
          <div className="divide-y divide-[var(--line-soft)]">
            {evidenceSummary.map((evidence) => (
              <article key={`${evidence.rank}-${evidence.source_id}`} className="grid gap-3 px-4 py-3 lg:grid-cols-[120px_minmax(0,1fr)]">
                <div className="text-xs text-[var(--ink-muted)]">
                  <p className="font-semibold text-[var(--ink-strong)]">Rank {evidence.rank}</p>
                  <p>score {evidence.importance_score ?? 0}</p>
                  {evidence.channel_id ? <p>{evidence.channel_id}</p> : null}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--ink-muted)]">
                    <span className="font-medium text-[var(--ink-strong)]">{evidence.source_id}</span>
                    {evidence.permission_level ? <span>{evidence.permission_level}</span> : null}
                    {evidence.timestamp ? <span>{evidence.timestamp}</span> : null}
                  </div>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--ink-muted)]">{evidence.snippet}</p>
                  {evidence.source_url ? (
                    <Link
                      href={evidence.source_url}
                      className="mt-2 inline-flex text-xs font-semibold text-[var(--workspace-rail-active)]"
                    >
                      Open source
                    </Link>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
        <div className="border-b border-[var(--line-soft)] px-4 py-4">
          <h3 className="text-sm font-semibold">Metadata</h3>
        </div>
        <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap p-4 text-xs leading-6 text-[var(--ink-muted)]">
          {JSON.stringify(run.metadata, null, 2)}
        </pre>
      </section>
    </div>
  );
}

type MetricIcon = typeof Sparkles;

function AdminOnlyNotice() {
  return (
    <section className="liquid-surface rounded-[32px] p-6">
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-1 h-5 w-5 text-amber-500" aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Admin observability</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal">Admin permission required</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Agent run details can include cost, prompt metadata, and evidence windows, so this view is restricted to workspace admins.
          </p>
          <Link
            href="/login"
            className="liquid-primary mt-4 inline-flex h-11 items-center justify-center rounded-[24px] px-5 text-sm font-semibold"
          >
            Go to login
          </Link>
        </div>
      </div>
    </section>
  );
}

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
    <div className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--ink-muted)]">{label}</span>
        <Icon className="h-4 w-4 text-[var(--ink-muted)]" aria-hidden="true" />
      </div>
      <p className="mt-3 truncate text-xl font-semibold">{value}</p>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">{label}</dt>
      <dd className="mt-1 truncate text-sm font-medium">{value}</dd>
    </div>
  );
}

function TokenRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-[#fbfaf8] px-3 py-2">
      <span className="text-sm text-[var(--ink-muted)]">{label}</span>
      <span className="text-sm font-semibold">{value.toLocaleString()}</span>
    </div>
  );
}

function formatDate(value: string) {
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
