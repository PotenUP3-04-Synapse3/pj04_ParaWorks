import { AlertTriangle, Bell, Bot, CheckCircle2, ExternalLink } from "lucide-react";
import Link from "next/link";
import { serverApiGet } from "@/lib/api/server";
import type { NotificationItem, NotificationsResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function NotificationsPage() {
  const data = await serverApiGet<NotificationsResponse>("/api/v1/notifications");

  return (
    <div className="space-y-5">
      <section className="liquid-surface rounded-[32px] p-5 md:p-7">
        <div className="relative flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <p className="text-sm font-semibold text-[var(--workspace-accent)]">Agent Alerts</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-normal">알림</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
              검토 큐와 에이전트 실행에서 바로 확인해야 할 항목만 모아봅니다.
            </p>
          </div>
          <div className="liquid-control inline-flex w-fit items-center gap-2 rounded-[24px] px-4 py-3 text-sm font-semibold text-[var(--ink-muted)]">
            <Bell className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            {data.counts.total} active alerts
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="검토" value={data.counts.review} />
        <SummaryCard label="AI 실행" value={data.counts.agent_runs} />
        <SummaryCard label="전체" value={data.counts.total} />
      </section>

      <section className="space-y-3">
        {data.notifications.map((item) => (
          <NotificationCard key={item.id} item={item} />
        ))}
        {data.notifications.length === 0 ? (
          <div className="liquid-surface rounded-[30px] px-5 py-10 text-sm text-[var(--ink-muted)]">
            지금 확인해야 할 알림이 없습니다.
          </div>
        ) : null}
      </section>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="liquid-surface rounded-[28px] p-5">
      <div className="relative">
        <p className="text-sm font-semibold text-[var(--ink-muted)]">{label}</p>
        <p className="mt-3 text-3xl font-semibold">{value}</p>
      </div>
    </div>
  );
}

function NotificationCard({ item }: { item: NotificationItem }) {
  const Icon = item.category === "agent_run" ? Bot : item.severity === "warning" ? AlertTriangle : CheckCircle2;

  return (
    <article className="liquid-surface rounded-[30px] p-5">
      <div className="relative flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex gap-3">
          <div className="liquid-primary grid h-11 w-11 shrink-0 place-items-center rounded-[22px]">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold">{item.title}</h3>
              <span className="rounded-full bg-[var(--glass-control)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                {item.severity}
              </span>
            </div>
            <p className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">{item.message}</p>
          </div>
        </div>
        <Link
          href={item.action_href}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-[22px] bg-[var(--glass-control-strong)] px-4 text-sm font-semibold text-[var(--ink-strong)]"
        >
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          열기
        </Link>
      </div>
    </article>
  );
}
