import { AlertTriangle, Bell, Bot, CheckCircle2, ExternalLink } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/knowledge/MemoryCollection";
import { serverApiGet } from "@/lib/api/server";
import type { NotificationItem, NotificationsResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function NotificationsPage() {
  const data = await serverApiGet<NotificationsResponse>("/api/v1/notifications").catch(() => null);

  if (!data) {
    return (
      <div className="reference-dashboard space-y-4">
        <div className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Agent Alerts</p>
            <h1>알림</h1>
            <p>이 화면은 개발되어 있으며 `/api/v1/notifications` 데이터를 사용합니다. 현재는 백엔드 API에 연결할 수 없습니다.</p>
          </div>
        </div>
        <EmptyState text="백엔드 API를 실행한 뒤 다시 확인해 주세요." />
      </div>
    );
  }

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Agent Alerts</p>
          <h1>알림</h1>
          <p>검토함과 에이전트 실행에서 바로 확인해야 할 항목만 모아봅니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Bell className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {data.counts.total.toLocaleString()} active alerts
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="검토 알림" value={data.counts.review} />
        <SummaryCard label="AI 실행 알림" value={data.counts.agent_runs} />
        <SummaryCard label="전체" value={data.counts.total} />
      </section>

      <section className="space-y-3">
        {data.notifications.map((item) => (
          <NotificationCard key={item.id} item={item} />
        ))}
        {data.notifications.length === 0 ? <EmptyState text="지금 확인해야 할 알림이 없습니다." /> : null}
      </section>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel reference-panel">
      <p className="text-[13px] font-bold text-muted">{label}</p>
      <p className="mt-3 text-3xl font-extrabold">{value.toLocaleString()}</p>
    </div>
  );
}

function NotificationCard({ item }: { item: NotificationItem }) {
  const Icon = item.category === "agent_run" ? Bot : item.severity === "warning" ? AlertTriangle : CheckCircle2;
  return (
    <article className="panel reference-panel">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex gap-3">
          <span className="source-logo blue h-11 w-11">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[15px] font-extrabold">{item.title}</h2>
              <span className="badge blue">{item.severity}</span>
              <span className="badge green">{item.category}</span>
            </div>
            <p className="mt-1 text-[13px] leading-6 text-muted">{item.message}</p>
          </div>
        </div>
        <Link href={item.action_href} className="primary-action max-w-[120px]">
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          열기
        </Link>
      </div>
    </article>
  );
}
