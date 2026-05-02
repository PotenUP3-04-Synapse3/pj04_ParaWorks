import { ClipboardList, GitBranch, History, Library, Route } from "lucide-react";
import Link from "next/link";
import { MemoryCard } from "@/components/knowledge/MemoryCollection";
import { apiGet } from "@/lib/api/client";
import type { KnowledgeItem, KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const collections = [
  {
    href: "/decisions",
    label: "결정",
    description: "승인된 의사결정과 판단 근거",
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
    description: "왜 그렇게 진행됐는지에 대한 맥락",
    key: "history_events",
    icon: History,
  },
  {
    href: "/review",
    label: "할 일",
    description: "근거가 확인된 후속 작업",
    key: "todos",
    icon: ClipboardList,
  },
] as const;

export default async function KnowledgePage() {
  const knowledge = await apiGet<KnowledgeResponse>("/api/v1/knowledge");
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
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-accent)]">Knowledge Library</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">승인된 회사 메모리</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
            Review Queue를 통과한 결정, 타임라인, 히스토리, 후속 작업을 근거와 함께 모아봅니다.
          </p>
        </div>
        <div className="liquid-surface inline-flex w-fit items-center gap-2 rounded-[26px] px-4 py-3 text-sm font-semibold">
          <Library className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {totalItems} approved records
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {collections.map((collection) => {
          const Icon = collection.icon;
          const count = knowledge.counts[collection.key];
          return (
            <Link
              key={collection.href}
              href={collection.href}
              className="liquid-surface rounded-[30px] p-5 transition hover:scale-[1.01]"
            >
              <div className="relative">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--ink-muted)]">{collection.label}</p>
                  <Icon className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
                </div>
                <p className="mt-4 text-3xl font-semibold">{count}</p>
                <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">{collection.description}</p>
              </div>
            </Link>
          );
        })}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold">최근 승인된 메모리</h3>
          <Link href="/review" className="text-xs font-semibold text-[var(--workspace-accent)] hover:underline">
            검토 큐 보기
          </Link>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {latestItems.map((item) => (
            <MemoryCard key={`${item.created_at}-${item.id}`} item={item as KnowledgeItem} />
          ))}
          {latestItems.length === 0 ? (
            <div className="liquid-surface rounded-[30px] px-5 py-10 text-sm text-[var(--ink-muted)]">
              아직 승인된 회사 메모리가 없습니다.
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
