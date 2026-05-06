import { GitBranch, Network, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeMapEdge, KnowledgeMapNode, KnowledgeMapResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const memoryTypeLabels: Record<string, string> = {
  decision: "Decision",
  timeline_event: "Timeline",
  history_event: "History",
  todo: "Todo",
};

function permissionTone(permissionLevel: string) {
  if (permissionLevel === "restricted") {
    return "text-[var(--workspace-accent)]";
  }
  if (permissionLevel === "public") {
    return "text-[var(--ink-muted)]";
  }
  return "text-[var(--ink-strong)]";
}

function findEvidenceForMemory(memoryNode: KnowledgeMapNode, edges: KnowledgeMapEdge[], nodesById: Map<string, KnowledgeMapNode>) {
  return edges
    .filter((edge) => edge.source === memoryNode.id)
    .map((edge) => nodesById.get(edge.target))
    .filter((node): node is KnowledgeMapNode => Boolean(node));
}

export default async function KnowledgeMapPage() {
  const map = await serverApiGet<KnowledgeMapResponse>("/api/v1/knowledge/map");
  const memoryNodes = map.nodes.filter((node) => node.type !== "evidence_source");
  const evidenceNodes = map.nodes.filter((node) => node.type === "evidence_source");
  const visibleEvidenceNodes = evidenceNodes.slice(0, 24);
  const nodesById = new Map(map.nodes.map((node) => [node.id, node]));

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-accent)]">Knowledge Map</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">승인된 회사 기억 연결도</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
            Review Queue를 통과한 결정, 타임라인, 히스토리, 할 일을 근거 링크와 연결해 한눈에 확인합니다.
          </p>
        </div>
        <div className="liquid-surface inline-flex w-fit items-center gap-2 rounded-[26px] px-4 py-3 text-sm font-semibold">
          <Network className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {map.counts.memory_nodes} memories / {map.counts.evidence_nodes} sources
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Memory nodes" value={map.counts.memory_nodes} />
        <MetricCard label="Evidence sources" value={map.counts.evidence_nodes} />
        <MetricCard label="Evidence edges" value={map.counts.edges} />
      </section>

      <section className="liquid-surface rounded-[30px] p-5">
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-stretch">
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
              Approved memory
            </div>
            {memoryNodes.map((node) => {
              const evidence = findEvidenceForMemory(node, map.edges, nodesById);
              return <MemoryMapCard key={node.id} node={node} evidence={evidence} />;
            })}
            {memoryNodes.length === 0 ? (
              <div className="rounded-[24px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-5 text-sm text-[var(--ink-muted)]">
                아직 맵에 표시할 승인된 회사 기억이 없습니다.
              </div>
            ) : null}
          </div>

          <div className="hidden w-px bg-[var(--line-soft)] lg:block" />

          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <GitBranch className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
              Source evidence
            </div>
            {visibleEvidenceNodes.map((node) => (
              <EvidenceNodeCard key={node.id} node={node} />
            ))}
            {evidenceNodes.length > visibleEvidenceNodes.length ? (
              <div className="rounded-[24px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-5 text-sm text-[var(--ink-muted)]">
                {evidenceNodes.length - visibleEvidenceNodes.length} more sources are available through the API.
              </div>
            ) : null}
            {evidenceNodes.length === 0 ? (
              <div className="rounded-[24px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-5 text-sm text-[var(--ink-muted)]">
                연결된 근거 링크가 아직 없습니다.
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="liquid-surface rounded-[30px] p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            <h3 className="text-base font-semibold">권한 분포</h3>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(map.counts.permission_levels).map(([level, count]) => (
              <span
                key={level}
                className="rounded-full bg-[var(--glass-control)] px-3 py-1.5 text-xs font-semibold text-[var(--ink-muted)]"
              >
                {level} {count}
              </span>
            ))}
            {Object.keys(map.counts.permission_levels).length === 0 ? (
              <span className="text-sm text-[var(--ink-muted)]">권한 정보가 없습니다.</span>
            ) : null}
          </div>
        </div>

        <div className="liquid-surface rounded-[30px] p-5">
          <p className="text-sm font-semibold text-[var(--workspace-accent)]">Cost policy</p>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
            이 맵은 승인된 DB 레코드와 source link만 집계합니다. LLM, embedding, sync job은 실행하지 않습니다.
          </p>
          <p className="mt-4 rounded-[22px] bg-[var(--panel-soft)] px-4 py-3 text-xs font-semibold text-[var(--ink-muted)]">
            {map.cost_policy.strategy}
          </p>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="liquid-surface rounded-[30px] p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">{label}</p>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function MemoryMapCard({ node, evidence }: { node: KnowledgeMapNode; evidence: KnowledgeMapNode[] }) {
  const visibleEvidence = evidence.slice(0, 4);
  return (
    <article className="rounded-[24px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-[var(--glass-control-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-strong)]">
          {memoryTypeLabels[node.type] ?? node.type}
        </span>
        <span className={`rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold ${permissionTone(node.permission_level)}`}>
          {node.permission_level}
        </span>
        {typeof node.confidence_score === "number" ? (
          <span className="rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
            {(node.confidence_score * 100).toFixed(0)}%
          </span>
        ) : null}
      </div>
      <h3 className="mt-3 text-sm font-semibold leading-6">{node.label}</h3>
      {node.summary ? <p className="mt-2 line-clamp-2 text-xs leading-5 text-[var(--ink-muted)]">{node.summary}</p> : null}
      <div className="mt-3 space-y-2">
        {visibleEvidence.map((source) => (
          <Link
            key={source.id}
            href={source.source_url ?? "/knowledge-map"}
            target={source.source_url ? "_blank" : undefined}
            className="flex items-center justify-between gap-3 rounded-[18px] bg-[var(--glass-control)] px-3 py-2 text-xs text-[var(--ink-muted)]"
          >
            <span className="min-w-0 truncate">{source.label}</span>
            <span className="shrink-0 text-[var(--workspace-accent)]">source</span>
          </Link>
        ))}
        {evidence.length > visibleEvidence.length ? (
          <div className="rounded-[18px] bg-[var(--glass-control)] px-3 py-2 text-xs font-semibold text-[var(--ink-muted)]">
            + {evidence.length - visibleEvidence.length} more supporting sources
          </div>
        ) : null}
      </div>
    </article>
  );
}

function EvidenceNodeCard({ node }: { node: KnowledgeMapNode }) {
  return (
    <article className="rounded-[24px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-semibold">{node.label}</p>
        <span className={`rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold ${permissionTone(node.permission_level)}`}>
          {node.permission_level}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--ink-muted)]">
        <span className="rounded-[16px] bg-[var(--glass-control)] px-3 py-2">
          memories {node.connected_memory_count ?? 0}
        </span>
        <span className="rounded-[16px] bg-[var(--glass-control)] px-3 py-2">
          snippets {node.snippet_count ?? 0}
        </span>
      </div>
    </article>
  );
}
