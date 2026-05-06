import { Suspense } from "react";
import { GoogleCallbackClient } from "./GoogleCallbackClient";

export default function GoogleOAuthCallbackPage() {
  return (
    <Suspense fallback={<GoogleCallbackFallback />}>
      <GoogleCallbackClient />
    </Suspense>
  );
}

function GoogleCallbackFallback() {
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-[var(--line-soft)] bg-white p-6 shadow-sm">
      <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">OAuth</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-normal">Google 연결 확인</h2>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
        Google에서 돌아온 인증 정보를 확인하고 있습니다.
      </p>
    </div>
  );
}
