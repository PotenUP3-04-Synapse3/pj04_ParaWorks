import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function TimelinePage() {
  const knowledge = await serverApiGet<KnowledgeResponse>("/api/v1/knowledge").catch(() => null);

  if (!knowledge) {
    return (
      <MemoryCollection
        eyebrow="Timeline"
        title="타임라인"
        description="이 화면은 개발되어 있으며 `/api/v1/knowledge`의 승인된 타임라인 이벤트를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다."
        items={[]}
        emptyText="백엔드 API를 실행한 뒤 다시 확인해 주세요."
        metricLabel="timeline events"
      />
    );
  }

  return (
    <MemoryCollection
      eyebrow="Timeline"
      title="타임라인"
      description="메일, Slack, 문서, 캘린더 근거에서 검토를 통과한 주요 사건을 시간 흐름으로 모읍니다."
      items={knowledge.timeline_events}
      emptyText="아직 승인된 타임라인 이벤트가 없습니다. 에이전트 후보를 검토하고 승인하면 이곳에 표시됩니다."
      metricLabel="timeline events"
    />
  );
}
