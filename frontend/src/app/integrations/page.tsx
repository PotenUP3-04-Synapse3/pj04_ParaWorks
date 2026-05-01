"use client";

import {
  Calendar,
  CheckCircle2,
  Database,
  Mail,
  MessageSquare,
  PlugZap,
  Radio,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { useJobStatus } from "@/hooks/useJobStatus";
import { apiPost } from "@/lib/api/client";
import type { IntegrationSyncResponse } from "@/lib/api/types";

const integrations = [
  {
    type: "slack",
    label: "Slack",
    icon: MessageSquare,
    status: "다음 우선순위",
    description: "채널 메시지를 수집해 타임라인과 히스토리 후보를 생성합니다.",
    accent: "bg-[#21132b] text-white",
  },
  {
    type: "gmail",
    label: "Gmail",
    icon: Mail,
    status: "메일 에이전트 준비",
    description: "메일 스레드를 요약하고 결정/후속 작업 후보를 추출합니다.",
    accent: "bg-blue-50 text-blue-700",
  },
  {
    type: "drive",
    label: "Drive",
    icon: Database,
    status: "문서 RAG 준비",
    description: "사내 문서와 버전을 보존하고 검색 가능한 근거로 연결합니다.",
    accent: "bg-emerald-50 text-emerald-700",
  },
  {
    type: "calendar",
    label: "Calendar",
    icon: Calendar,
    status: "맥락 보강",
    description: "회의 일정을 히스토리 이벤트의 시간 맥락으로 활용합니다.",
    accent: "bg-amber-50 text-amber-700",
  },
];

export default function IntegrationsPage() {
  const [activeJobId, setActiveJobId] = useState<string>();
  const [syncResult, setSyncResult] = useState<IntegrationSyncResponse>();
  const [pendingType, setPendingType] = useState<string>();
  const [error, setError] = useState<string>();
  const jobStatus = useJobStatus(activeJobId);

  async function startSync(type: string) {
    setPendingType(type);
    setError(undefined);

    try {
      const result = await apiPost<IntegrationSyncResponse>(`/api/v1/integrations/${type}/sync`);
      setSyncResult(result);
      setActiveJobId(result.job_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "동기화에 실패했습니다.");
    } finally {
      setPendingType(undefined);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Tools</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">연동과 에이전트 도구</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Slack, 메일, 문서, 캘린더 데이터를 ParaWorks의 Review Queue와 RAG 흐름으로 연결합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <PlugZap className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          Mock connector smoke mode
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-4 sm:grid-cols-2">
          {integrations.map((integration) => {
            const Icon = integration.icon;
            const pending = pendingType === integration.type;
            const featured = integration.type === "slack";
            return (
              <article
                key={integration.type}
                className={`rounded-lg border bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                  featured ? "border-[#c9b7d5]" : "border-[var(--line-soft)]"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${integration.accent}`}>
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold">{integration.label}</h3>
                        {featured ? (
                          <span className="rounded-full bg-[var(--workspace-accent)] px-2 py-0.5 text-xs font-bold text-[#13231f]">
                            추천
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs font-semibold text-[var(--workspace-rail-active)]">
                        {integration.status}
                      </p>
                    </div>
                  </div>
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" aria-hidden="true" />
                </div>

                <p className="mt-4 min-h-12 text-sm leading-6 text-[var(--ink-muted)]">
                  {integration.description}
                </p>

                <div className="mt-4 flex items-center justify-between gap-3 border-t border-[var(--line-soft)] pt-4">
                  <span className="text-xs text-[var(--ink-muted)]">현재 mock 데이터 사용</span>
                  <button
                    type="button"
                    onClick={() => void startSync(integration.type)}
                    disabled={Boolean(pendingType)}
                    className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-neutral-300 disabled:bg-neutral-300"
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {pending ? "동기화 중" : "동기화"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        <aside className="rounded-lg border border-[var(--line-soft)] bg-white shadow-sm">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-[var(--workspace-rail-active)]" aria-hidden="true" />
              <h3 className="text-sm font-semibold">작업 스트림</h3>
            </div>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">동기화와 Review 후보 생성 상태</p>
          </div>

          <div className="p-4">
            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {error}
              </div>
            ) : null}

            {syncResult ? (
              <div className="space-y-3 text-sm">
                <div className="rounded-lg bg-[#fbfaf8] p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                    Job
                  </p>
                  <p className="mt-1 break-all font-medium">{syncResult.job_id}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-[#fbfaf8] p-3">
                    <p className="text-xs text-[var(--ink-muted)]">Connector</p>
                    <p className="mt-1 font-semibold capitalize">{syncResult.connector_type}</p>
                  </div>
                  <div className="rounded-lg bg-[#fbfaf8] p-3">
                    <p className="text-xs text-[var(--ink-muted)]">Review items</p>
                    <p className="mt-1 font-semibold">{syncResult.created_review_items}</p>
                  </div>
                </div>
                <div className="rounded-lg border border-[var(--line-soft)] bg-white p-3">
                  <p className="mb-2 flex items-center gap-2 text-xs font-semibold text-[var(--ink-muted)]">
                    <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                    SSE status
                  </p>
                  <pre className="max-h-52 overflow-auto whitespace-pre-wrap rounded-md bg-[#21132b] p-3 text-xs leading-5 text-white/82">
                    {jobStatus || syncResult.status}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-[var(--line-soft)] bg-[#fbfaf8] p-5 text-sm leading-6 text-[var(--ink-muted)]">
                왼쪽 도구에서 동기화를 실행하면 여기에서 작업 스트림과 생성된 Review 후보 수를 확인할 수 있습니다.
              </div>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}
