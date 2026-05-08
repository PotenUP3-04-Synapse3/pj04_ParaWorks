import { ClipboardList, GitBranch, History, Library, Network, Route } from "lucide-react";
import Link from "next/link";
import { EmptyState, MemoryCard } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { KnowledgeItem, KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const collections = [
  {
    href: "/decisions",
    label: "의사결정",
    description: "승인된 결정과 판단 근거",
    key: "decisions",
    icon: GitBranch,
  },
  {
    href: "/timeline",
    label: "타임라인",
    description: "검토를 통과한 주요 발생 기록",
    key: "timeline_events",
    icon: Route,
  },
  {
    href: "/history",
    label: "히스토리",
    description: "업무 맥락과 진행 배경",
    key: "history_events",
    icon: History,
  },
  {
    href: "/review",
    label: "할 일 후보",
    description: "검토가 필요한 후속 작업",
    key: "todos",
    icon: ClipboardList,
  },
] as const;

export default async function KnowledgePage() {
  const knowledge = await serverApiGet<KnowledgeResponse>("/api/v1/knowledge").catch(() => null);

  if (!knowledge) {
    return (
      <div className="reference-dashboard space-y-4">
        <div className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Knowledge Library</p>
            <h1>승인된 회사 메모리</h1>
            <p>이 화면은 개발되어 있으며 `/api/v1/knowledge` 데이터를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다.</p>
          </div>
        </div>
        <EmptyState text="백엔드 API를 실행한 뒤 다시 확인해 주세요." />
      </div>
    );
  }

  const totalItems =
    knowledge.counts.decisions +
    knowledge.counts.timeline_events +
    knowledge.counts.history_events +
    knowledge.counts.todos;
  const latestItems = [
    ...knowledge.decisions,
    ...knowledge.timeline_events,
    ...knowledge.history_events,
    ...knowledge.todos,
  ]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 4);

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Knowledge Library</p>
          <h1>승인된 회사 메모리</h1>
          <p>Review Queue를 통과한 결정, 타임라인, 히스토리, 할 일을 근거와 함께 모아봅니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Library className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {totalItems.toLocaleString()} approved records
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {collections.map((collection) => {
          const Icon = collection.icon;
          const count = knowledge.counts[collection.key];
          return (
            <Link key={collection.href} href={collection.href} className="panel reference-panel transition hover:shadow-lg">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[13px] font-extrabold text-ink">{collection.label}</p>
                <Icon className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
              </div>
              <p className="mt-4 text-3xl font-extrabold">{count.toLocaleString()}</p>
              <p className="mt-2 text-[12px] leading-5 text-muted">{collection.description}</p>
            </Link>
          );
        })}
      </section>

      <Link href="/knowledge-map" className="panel reference-panel flex flex-col gap-4 transition hover:shadow-lg md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Knowledge Map</p>
          <h2 className="mt-1 text-[17px] font-extrabold">승인된 기억과 근거 연결 보기</h2>
          <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted">
            어떤 source evidence가 결정, 타임라인, 히스토리를 지지하는지 읽기 전용 그래프로 확인합니다.
          </p>
        </div>
        <span className="primary-action max-w-[160px]">
          <Network className="h-4 w-4" aria-hidden="true" />
          맵 열기
        </span>
      </Link>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-extrabold">최근 승인된 메모리</h2>
          <Link href="/review" className="text-link">검토함 보기</Link>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {latestItems.map((item) => (
            <MemoryCard key={`${item.created_at}-${item.id}`} item={item as KnowledgeItem} />
          ))}
          {latestItems.length === 0 ? <EmptyState text="아직 승인된 회사 메모리가 없습니다." /> : null}
        </div>
      </section>
    </div>
  );
}
