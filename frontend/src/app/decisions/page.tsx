import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { apiGet } from "@/lib/api/client";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function DecisionsPage() {
  const knowledge = await apiGet<KnowledgeResponse>("/api/v1/knowledge");

  return (
    <MemoryCollection
      eyebrow="Decision Records"
      title="결정 기록"
      description="AI 에이전트가 후보를 만들고 사람이 승인한 의사결정만 모아봅니다. 각 기록은 근거 링크, confidence, 권한 정보를 함께 보존합니다."
      items={knowledge.decisions}
      emptyText="아직 승인된 결정 기록이 없습니다."
      metricLabel="decisions"
    />
  );
}
