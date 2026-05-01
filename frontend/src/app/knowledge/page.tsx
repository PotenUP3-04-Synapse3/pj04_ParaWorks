import { CheckCircle2, ClipboardList, GitBranch, History, Library, Link2 } from "lucide-react";
import { apiGet } from "@/lib/api/client";
import type { KnowledgeItem, KnowledgeResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function KnowledgePage() {
  const knowledge = await apiGet<KnowledgeResponse>("/api/v1/knowledge");
  const totalItems = knowledge.counts.decisions + knowledge.counts.history_events + knowledge.counts.todos;

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Knowledge Library</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">승인된 회사 메모리</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Review Queue에서 승인된 결정, 히스토리, 할 일을 근거와 함께 보관합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <Library className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {totalItems} approved records
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        <SummaryCard icon={GitBranch} label="결정" value={knowledge.counts.decisions} />
        <SummaryCard icon={History} label="히스토리" value={knowledge.counts.history_events} />
        <SummaryCard icon={ClipboardList} label="할 일" value={knowledge.counts.todos} />
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <KnowledgeSection
          title="결정 기록"
          description="승인된 결정과 판단 근거"
          emptyText="아직 승인된 결정 기록이 없습니다."
          items={knowledge.decisions}
        />
        <KnowledgeSection
          title="히스토리"
          description="프로젝트 타임라인에 남길 사건"
          emptyText="아직 승인된 히스토리가 없습니다."
          items={knowledge.history_events}
        />
        <KnowledgeSection
          title="할 일"
          description="근거가 확인된 후속 작업"
          emptyText="아직 승인된 할 일이 없습니다."
          items={knowledge.todos}
        />
      </section>
    </div>
  );
}

type SummaryIcon = typeof GitBranch;

function SummaryCard({
  icon: Icon,
  label,
  value,
}: {
  icon: SummaryIcon;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--ink-muted)]">{label}</span>
        <Icon className="h-4 w-4 text-[var(--ink-muted)]" aria-hidden="true" />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function KnowledgeSection({
  title,
  description,
  emptyText,
  items,
}: {
  title: string;
  description: string;
  emptyText: string;
  items: KnowledgeItem[];
}) {
  return (
    <article className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
      <div className="border-b border-[var(--line-soft)] px-4 py-4">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">{description}</p>
      </div>
      <div className="divide-y divide-[var(--line-soft)]">
        {items.map((item) => (
          <KnowledgeCard key={item.id} item={item} />
        ))}
        {items.length === 0 ? (
          <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">{emptyText}</p>
        ) : null}
      </div>
    </article>
  );
}

function KnowledgeCard({ item }: { item: KnowledgeItem }) {
  return (
    <div className="space-y-3 px-4 py-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-[#ecfbf6] px-2 py-0.5 text-xs font-semibold text-[#0f6f58]">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            {item.review_status}
          </span>
          <span className="rounded-full bg-[#fbfaf8] px-2 py-0.5 text-xs font-semibold text-[var(--ink-muted)]">
            {item.permission_level}
          </span>
          {item.priority ? (
            <span className="rounded-full bg-[#fff7ed] px-2 py-0.5 text-xs font-semibold text-[#9a3412]">
              {item.priority}
            </span>
          ) : null}
        </div>
        <h4 className="mt-2 text-sm font-semibold leading-6">{item.title}</h4>
        <p className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">{item.summary}</p>
      </div>

      <div className="rounded-lg bg-[#fbfaf8] p-3">
        <p className="text-xs font-semibold text-[var(--ink-muted)]">
          confidence {(item.confidence_score * 100).toFixed(0)}%
        </p>
        {item.source_snippets[0] ? (
          <p className="mt-2 border-l-2 border-[var(--line-soft)] pl-3 text-xs leading-5 text-[var(--ink-muted)]">
            {item.source_snippets[0]}
          </p>
        ) : null}
      </div>

      {item.source_links[0] ? (
        <a
          href={item.source_links[0]}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs font-semibold text-[#21132b] underline-offset-4 hover:underline"
        >
          <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
          근거 열기
        </a>
      ) : null}
    </div>
  );
}
