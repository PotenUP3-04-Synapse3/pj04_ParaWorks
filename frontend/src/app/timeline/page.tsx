import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { apiGet } from "@/lib/api/client";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function TimelinePage() {
  const knowledge = await apiGet<KnowledgeResponse>("/api/v1/knowledge");

  return (
    <MemoryCollection
      eyebrow="Timeline"
      title="업무 타임라인"
      description="메일, Slack, 문서, 캘린더에서 검토를 통과한 발생 기록을 시간순 회사 메모리로 확인합니다."
      items={knowledge.timeline_events}
      emptyText="아직 승인된 타임라인 이벤트가 없습니다."
      metricLabel="timeline events"
    />
  );
}
