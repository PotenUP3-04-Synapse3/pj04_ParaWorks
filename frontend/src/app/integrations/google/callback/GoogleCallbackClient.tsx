"use client";

import { AlertCircle, CheckCircle2, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { IntegrationConnection } from "@/lib/api/types";

type CallbackState =
  | { status: "idle" | "loading" }
  | { status: "success"; connection: IntegrationConnection }
  | { status: "error"; message: string };

export function GoogleCallbackClient() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const googleError = searchParams.get("error");
  const [callbackState, setCallbackState] = useState<CallbackState>({ status: "idle" });

  const missingCallbackParams = useMemo(() => !code || !state, [code, state]);

  useEffect(() => {
    if (googleError) {
      setCallbackState({
        status: "error",
        message: `Google 인증이 취소되었거나 실패했습니다. (${googleError})`,
      });
      return;
    }

    if (missingCallbackParams) {
      setCallbackState({
        status: "error",
        message: "Google 연결 정보를 확인할 수 없습니다.",
      });
      return;
    }

    let active = true;
    const callbackCode = code;
    const callbackStateValue = state;
    if (!callbackCode || !callbackStateValue) {
      return undefined;
    }

    const query = new URLSearchParams({ code: callbackCode, state: callbackStateValue });
    setCallbackState({ status: "loading" });

    apiGet<IntegrationConnection>(`/api/v1/integrations/google/oauth/callback?${query.toString()}`)
      .then((connection) => {
        if (active) {
          setCallbackState({ status: "success", connection });
        }
      })
      .catch((caught) => {
        if (active) {
          setCallbackState({
            status: "error",
            message: formatCallbackError(caught),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [code, googleError, missingCallbackParams, state]);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">OAuth</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">Google 연결 확인</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
          Gmail과 Google Drive 인증 결과를 ParaWorks 연결 상태로 저장합니다. 토큰 원문과 내부 token reference는 화면에 표시하지 않습니다.
        </p>
      </div>

      <section className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-5 shadow-sm">
        {callbackState.status === "success" ? (
          <SuccessPanel connection={callbackState.connection} />
        ) : callbackState.status === "error" ? (
          <ErrorPanel message={callbackState.message} />
        ) : (
          <LoadingPanel />
        )}
      </section>
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-700">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
      </span>
      <div>
        <h3 className="text-base font-semibold">인증 정보를 확인하는 중</h3>
        <p className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">
          Google OAuth code와 signed state를 backend callback으로 전달하고 연결 메타데이터만 저장합니다.
        </p>
      </div>
    </div>
  );
}

function SuccessPanel({ connection }: { connection: IntegrationConnection }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
          <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h3 className="text-base font-semibold">Google 연결 완료</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">
            {connection.workspace_name} 계정이 ParaWorks에 연결되었습니다.
          </p>
        </div>
      </div>

      <dl className="grid gap-3 rounded-lg bg-[var(--glass-strong)] p-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold text-[var(--ink-muted)]">Connector</dt>
          <dd className="mt-1 font-semibold">{formatConnectorName(connection.connector_type)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold text-[var(--ink-muted)]">Status</dt>
          <dd className="mt-1 font-semibold">{connection.status}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold text-[var(--ink-muted)]">Scopes</dt>
          <dd className="mt-1 font-semibold">{connection.scopes.length.toLocaleString()}개</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold text-[var(--ink-muted)]">Masked token</dt>
          <dd className="mt-1 font-semibold">{connection.masked_bot_token}</dd>
        </div>
      </dl>

      <Link
        href="/integrations"
        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-4 text-sm font-semibold text-white"
      >
        <ExternalLink className="h-4 w-4" aria-hidden="true" />
        연동 페이지로 돌아가기
      </Link>
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-red-50 text-red-700">
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h3 className="text-base font-semibold">Google 연결을 완료하지 못했습니다.</h3>
          <p className="mt-1 text-sm leading-6 text-red-700">{message}</p>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
            Google Cloud OAuth Client의 승인된 리디렉션 URI에 `GOOGLE_OAUTH_REDIRECT_URI` 값이 정확히 등록되어 있어야 합니다.
          </p>
        </div>
      </div>

      <Link
        href="/integrations"
        className="inline-flex h-10 items-center justify-center rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-4 text-sm font-semibold text-[#21132b] shadow-sm hover:bg-[var(--glass-strong)]"
      >
        연동 페이지로 돌아가기
      </Link>
    </div>
  );
}

function formatConnectorName(connectorType: string) {
  if (connectorType === "gmail") {
    return "Gmail";
  }
  if (connectorType === "drive") {
    return "Google Drive";
  }
  if (connectorType === "calendar") {
    return "Google Calendar";
  }
  return connectorType;
}

function formatCallbackError(caught: unknown) {
  if (!(caught instanceof Error)) {
    return "Google 연결 처리 중 알 수 없는 오류가 발생했습니다.";
  }

  if (caught.message.includes("invalid_grant")) {
    return "Google 인증 코드가 만료되었거나 이미 사용되었습니다. 연동 페이지에서 다시 연결해 주세요.";
  }

  if (caught.message.includes("redirect_uri")) {
    return "Google Cloud에 등록된 Redirect URI와 ParaWorks 설정값이 일치하지 않습니다.";
  }

  return "Google 연결 처리 중 오류가 발생했습니다. Google OAuth 설정과 ParaWorks 환경 변수를 확인해 주세요.";
}
