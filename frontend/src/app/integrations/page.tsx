"use client";

import { Calendar, Database, Mail, MessageSquare } from "lucide-react";
import { useState } from "react";
import { useJobStatus } from "@/hooks/useJobStatus";
import { apiPost } from "@/lib/api/client";
import type { IntegrationSyncResponse } from "@/lib/api/types";

const integrations = [
  { type: "drive", label: "Drive", icon: Database },
  { type: "gmail", label: "Gmail", icon: Mail },
  { type: "slack", label: "Slack", icon: MessageSquare },
  { type: "calendar", label: "Calendar", icon: Calendar },
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
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-muted">Mock 커넥터</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">연동</h2>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {integrations.map((integration) => {
          const Icon = integration.icon;
          const pending = pendingType === integration.type;
          return (
            <div key={integration.type} className="rounded-md border border-line bg-white p-4">
              <div className="flex h-10 items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="grid h-9 w-9 place-items-center rounded-md border border-line">
                    <Icon className="h-4 w-4 text-muted" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold">{integration.label}</h3>
                    <p className="text-xs text-muted">mock 준비됨</p>
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void startSync(integration.type)}
                disabled={Boolean(pendingType)}
                className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-line bg-neutral-900 px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {pending ? "동기화 중" : "동기화"}
              </button>
            </div>
          );
        })}
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <h3 className="text-sm font-semibold">작업 상태</h3>
        <div className="mt-3 min-h-24 rounded-md border border-line bg-neutral-50 p-3">
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          {syncResult ? (
            <div className="space-y-2 text-sm">
              <p>
                <span className="font-medium">작업:</span> {syncResult.job_id}
              </p>
              <p>
                <span className="font-medium">커넥터:</span> {syncResult.connector_type}
              </p>
              <p>
                <span className="font-medium">생성된 검토 항목:</span>{" "}
                {syncResult.created_review_items}
              </p>
              <p>
                <span className="font-medium">스트림:</span> {jobStatus || syncResult.status}
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted">동기화를 실행하면 작업 스트림을 볼 수 있습니다.</p>
          )}
        </div>
      </section>
    </div>
  );
}
