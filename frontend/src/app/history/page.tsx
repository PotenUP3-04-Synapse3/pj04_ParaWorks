import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const knowledge = await serverApiGet<KnowledgeResponse>("/api/v1/knowledge").catch(() => null);

  if (!knowledge) {
    return (
      <MemoryCollection
        eyebrow="History"
        title="히스토리"
        description="이 화면은 개발되어 있으며 `/api/v1/knowledge`의 승인된 히스토리 데이터를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다."
        items={[]}
        emptyText="백엔드 API를 실행한 뒤 다시 확인해 주세요."
        metricLabel="history records"
      />
    );
  }

  return (
    <MemoryCollection
      eyebrow="History"
      title="히스토리"
      description="왜 그렇게 진행됐는지, 일정과 결정의 배경이 무엇인지 승인된 근거와 함께 정리합니다."
      items={knowledge.history_events}
      emptyText="아직 승인된 히스토리 기록이 없습니다. Review Queue 승인 후 이곳에서 확인할 수 있습니다."
      metricLabel="history records"
    />
  );
}
