import { Suspense } from "react";
import { SlackCallbackClient } from "./SlackCallbackClient";

export default function SlackOAuthCallbackPage() {
  return (
    <Suspense fallback={<SlackCallbackFallback />}>
      <SlackCallbackClient />
    </Suspense>
  );
}

function SlackCallbackFallback() {
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-6 shadow-sm">
      <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">OAuth</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-normal">Slack 연결 확인</h2>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">Slack에서 돌아온 인증 정보를 확인하고 있습니다.</p>
    </div>
  );
}
