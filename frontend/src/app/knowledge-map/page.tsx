import { GitBranch, Network, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeMapEdge, KnowledgeMapNode, KnowledgeMapResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const memoryTypeLabels: Record<string, string> = {
  decision: "의사결정",
  timeline_event: "타임라인",
  history_event: "히스토리",
  todo: "할 일",
};

function findEvidenceForMemory(memoryNode: KnowledgeMapNode, edges: KnowledgeMapEdge[], nodesById: Map<string, KnowledgeMapNode>) {
  return edges
    .filter((edge) => edge.source === memoryNode.id)
    .map((edge) => nodesById.get(edge.target))
    .filter((node): node is KnowledgeMapNode => Boolean(node));
}

export default async function KnowledgeMapPage() {
  const map = await serverApiGet<KnowledgeMapResponse>("/api/v1/knowledge/map").catch(() => null);

  if (!map) {
    return (
      <div className="reference-dashboard space-y-4">
        <div className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Knowledge Map</p>
            <h1>승인된 기억과 근거 연결</h1>
            <p>이 화면은 개발되어 있으며 `/api/v1/knowledge/map` 데이터를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다.</p>
          </div>
        </div>
        <EmptyState text="백엔드 API를 실행한 뒤 다시 확인해 주세요." />
      </div>
    );
  }

  const memoryNodes = map.nodes.filter((node) => node.type !== "evidence_source");
  const evidenceNodes = map.nodes.filter((node) => node.type === "evidence_source");
  const visibleEvidenceNodes = evidenceNodes.slice(0, 24);
  const nodesById = new Map(map.nodes.map((node) => [node.id, node]));

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Knowledge Map</p>
          <h1>승인된 기억과 근거 연결</h1>
          <p>Review Queue를 통과한 회사 메모리와 source evidence의 연결을 읽기 전용으로 확인합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Network className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {map.counts.memory_nodes} memories / {map.counts.evidence_nodes} sources
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Memory nodes" value={map.counts.memory_nodes} />
        <MetricCard label="Evidence sources" value={map.counts.evidence_nodes} />
        <MetricCard label="Evidence edges" value={map.counts.edges} />
      </section>

      <section className="panel reference-panel">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="min-w-0 space-y-3">
            <div className="flex items-center gap-2 text-[14px] font-extrabold">
              <ShieldCheck className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
              승인된 메모리
            </div>
            {memoryNodes.map((node) => {
              const evidence = findEvidenceForMemory(node, map.edges, nodesById);
              return <MemoryMapCard key={node.id} node={node} evidence={evidence} />;
            })}
            {memoryNodes.length === 0 ? <EmptyState text="아직 맵에 표시할 승인된 회사 메모리가 없습니다." /> : null}
          </div>

          <div className="min-w-0 space-y-3">
            <div className="flex items-center gap-2 text-[14px] font-extrabold">
              <GitBranch className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
              Source evidence
            </div>
            {visibleEvidenceNodes.map((node) => (
              <EvidenceNodeCard key={node.id} node={node} />
            ))}
            {evidenceNodes.length > visibleEvidenceNodes.length ? (
              <div className="rounded-lg border border-line bg-surface-soft p-4 text-[13px] text-muted">
                API에는 {evidenceNodes.length - visibleEvidenceNodes.length}개의 추가 source가 더 있습니다.
              </div>
            ) : null}
            {evidenceNodes.length === 0 ? <EmptyState text="연결된 근거 source가 아직 없습니다." /> : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="panel reference-panel">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            <h2 className="text-[15px] font-extrabold">권한 분포</h2>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(map.counts.permission_levels).map(([level, count]) => (
              <span key={level} className="badge blue">
                {level} {count}
              </span>
            ))}
            {Object.keys(map.counts.permission_levels).length === 0 ? (
              <span className="text-[13px] text-muted">권한 정보가 없습니다.</span>
            ) : null}
          </div>
        </div>

        <div className="panel reference-panel">
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Cost policy</p>
          <p className="mt-2 text-[13px] leading-6 text-muted">
            이 맵은 승인된 DB 레코드와 source link만 집계합니다. LLM, embedding, sync job은 실행하지 않습니다.
          </p>
          <p className="mt-4 rounded-lg bg-surface-soft px-4 py-3 text-[12px] font-bold text-muted">
            {map.cost_policy.strategy}
          </p>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel reference-panel">
      <p className="text-[12px] font-bold uppercase text-muted">{label}</p>
      <p className="mt-3 text-3xl font-extrabold">{value.toLocaleString()}</p>
    </div>
  );
}

function MemoryMapCard({ node, evidence }: { node: KnowledgeMapNode; evidence: KnowledgeMapNode[] }) {
  const visibleEvidence = evidence.slice(0, 4);
  return (
    <article className="rounded-lg border border-line bg-surface-soft p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="badge green">{memoryTypeLabels[node.type] ?? node.type}</span>
        <span className="badge blue">{node.permission_level}</span>
        {typeof node.confidence_score === "number" ? (
          <span className="badge violet">{(node.confidence_score * 100).toFixed(0)}%</span>
        ) : null}
      </div>
      <h2 className="mt-3 text-[14px] font-extrabold leading-6">{node.label}</h2>
      {node.summary ? <p className="mt-2 line-clamp-2 text-[12px] leading-5 text-muted">{node.summary}</p> : null}
      <div className="mt-3 space-y-2">
        {visibleEvidence.map((source) => (
          <Link
            key={source.id}
            href={source.source_url ?? "/knowledge-map"}
            target={source.source_url ? "_blank" : undefined}
            className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-[12px] text-muted"
          >
            <span className="min-w-0 truncate">{source.label}</span>
            <span className="shrink-0 text-[var(--primary-dark)]">source</span>
          </Link>
        ))}
        {evidence.length > visibleEvidence.length ? (
          <div className="rounded-lg bg-white px-3 py-2 text-[12px] font-bold text-muted">
            + {evidence.length - visibleEvidence.length} more supporting sources
          </div>
        ) : null}
      </div>
    </article>
  );
}

function EvidenceNodeCard({ node }: { node: KnowledgeMapNode }) {
  return (
    <article className="rounded-lg border border-line bg-surface-soft p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 truncate text-[14px] font-extrabold">{node.label}</p>
        <span className="badge blue">{node.permission_level}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-muted">
        <span className="rounded-lg bg-white px-3 py-2">memories {node.connected_memory_count ?? 0}</span>
        <span className="rounded-lg bg-white px-3 py-2">snippets {node.snippet_count ?? 0}</span>
      </div>
    </article>
  );
}
