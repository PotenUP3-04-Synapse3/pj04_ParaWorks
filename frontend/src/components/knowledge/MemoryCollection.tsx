import { CheckCircle2, ExternalLink, ShieldCheck } from "lucide-react";
import type { KnowledgeItem } from "@/lib/api/types";

type MemoryCollectionProps = {
  eyebrow: string;
  title: string;
  description: string;
  items: KnowledgeItem[];
  emptyText: string;
  metricLabel: string;
};

export function MemoryCollection({
  eyebrow,
  title,
  description,
  items,
  emptyText,
  metricLabel,
}: MemoryCollectionProps) {
  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-accent)]">{eyebrow}</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">{title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">{description}</p>
        </div>
        <div className="liquid-surface inline-flex w-fit items-center gap-2 rounded-[26px] px-4 py-3 text-sm font-semibold">
          <ShieldCheck className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          {items.length} {metricLabel}
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <MemoryCard key={item.id} item={item} />
        ))}
        {items.length === 0 ? (
          <div className="liquid-surface rounded-[30px] px-5 py-10 text-sm text-[var(--ink-muted)]">
            {emptyText}
          </div>
        ) : null}
      </section>
    </div>
  );
}

export function MemoryCard({ item }: { item: KnowledgeItem }) {
  return (
    <article className="liquid-surface rounded-[30px] p-5">
      <div className="relative space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--glass-control-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-strong)]">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--workspace-accent)]" aria-hidden="true" />
            {item.review_status}
          </span>
          <span className="rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
            {item.permission_level}
          </span>
          {item.priority ? (
            <span className="rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold text-[var(--workspace-accent)]">
              {item.priority}
            </span>
          ) : null}
        </div>

        <div>
          <h3 className="text-base font-semibold leading-6">{item.title}</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">{item.summary}</p>
        </div>

        <div className="rounded-[22px] border border-[var(--line-soft)] bg-[var(--panel-soft)] p-4">
          <p className="text-xs font-semibold text-[var(--ink-muted)]">
            confidence {(item.confidence_score * 100).toFixed(0)}%
          </p>
          {item.source_snippets[0] ? (
            <p className="mt-2 border-l-2 border-[var(--line-strong)] pl-3 text-xs leading-5 text-[var(--ink-muted)]">
              {item.source_snippets[0]}
            </p>
          ) : null}
        </div>

        {item.source_links[0] ? (
          <a
            href={item.source_links[0]}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--workspace-accent)] underline-offset-4 hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            근거 열기
          </a>
        ) : null}
      </div>
    </article>
  );
}
