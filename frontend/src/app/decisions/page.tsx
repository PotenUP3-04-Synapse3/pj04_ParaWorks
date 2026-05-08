import { MemoryCollection } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function DecisionsPage() {
  const knowledge = await serverApiGet<KnowledgeResponse>("/api/v1/knowledge").catch(() => null);

  if (!knowledge) {
    return (
      <MemoryCollection
        eyebrow="Decision Records"
        title="의사결정"
        description="이 화면은 개발되어 있으며 `/api/v1/knowledge`의 승인된 의사결정 데이터를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다."
        items={[]}
        emptyText="백엔드 API를 실행한 뒤 다시 확인해 주세요."
        metricLabel="decisions"
      />
    );
  }

  return (
    <MemoryCollection
      eyebrow="Decision Records"
      title="의사결정"
      description="Review Queue에서 승인된 의사결정 기록입니다. 각 항목은 근거 링크, 스니펫, 신뢰도, 권한 정보를 함께 보존합니다."
      items={knowledge.decisions}
      emptyText="아직 승인된 의사결정 기록이 없습니다. Review Queue에서 후보를 승인하면 이곳에 표시됩니다."
      metricLabel="decisions"
    />
  );
}
