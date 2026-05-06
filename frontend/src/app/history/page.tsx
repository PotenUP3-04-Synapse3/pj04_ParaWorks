import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const knowledge = await serverApiGet<KnowledgeResponse>("/api/v1/knowledge");

  return (
    <MemoryCollection
      eyebrow="History"
      title="업무 히스토리"
      description="결정이 내려진 이유, 일정이 바뀐 배경, 업무 맥락을 승인된 근거와 함께 정리합니다."
      items={knowledge.history_events}
      emptyText="아직 승인된 히스토리 기록이 없습니다."
      metricLabel="history records"
    />
  );
}
