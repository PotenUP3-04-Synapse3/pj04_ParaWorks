"use client";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DEMO_USER_STORAGE_KEY, apiGet, setStoredDemoUserId } from "@/lib/api/client";
import type { AuthUserResponse } from "@/lib/api/types";

type CallbackState = "loading" | "success" | "error";

export default function GoogleLoginCallbackPage() {
  return (
    <main className="login-callback-page" data-testid="google-login-callback-page">
      <Suspense fallback={<CallbackStatus status="loading" message="Google 로그인 결과를 확인하고 있습니다." />}>
        <GoogleLoginCallbackClient />
      </Suspense>
    </main>
  );
}

function GoogleLoginCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<CallbackState>("loading");
  const [message, setMessage] = useState("Google 로그인 결과를 확인하고 있습니다.");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");

    if (error) {
      setStatus("error");
      setMessage(`Google 로그인이 취소되었거나 실패했습니다. (${error})`);
      return;
    }

    if (!code || !state) {
      setStatus("error");
      setMessage("Google 로그인 정보를 확인할 수 없습니다.");
      return;
    }

    const query = new URLSearchParams({ code, state });
    apiGet<AuthUserResponse>(`/api/v1/auth/google/callback?${query.toString()}`)
      .then((result) => {
        setStoredDemoUserId(result.user.id);
        window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: result.user.id }));
        setStatus("success");
        setMessage(`${result.user.name} 계정으로 로그인되었습니다.`);
        window.setTimeout(() => router.replace("/dashboard"), 650);
      })
      .catch((callbackError: Error) => {
        setStatus("error");
        setMessage(callbackError.message || "초대되지 않은 Google 계정이거나 로그인을 완료하지 못했습니다.");
      });
  }, [router, searchParams]);

  return <CallbackStatus status={status} message={message} />;
}

function CallbackStatus({ status, message }: { status: CallbackState; message: string }) {
  const Icon = status === "loading" ? Loader2 : status === "success" ? CheckCircle2 : AlertTriangle;
  const title = status === "loading" ? "로그인 확인 중" : status === "success" ? "로그인 완료" : "로그인 확인 실패";

  return (
    <section className={`login-callback-card ${status}`} data-testid="google-login-callback-status" role="status" aria-live="polite">
      <div className="login-callback-icon">
        <Icon className={status === "loading" ? "animate-spin" : ""} aria-hidden="true" />
      </div>
      <p>Google Identity</p>
      <h1>{title}</h1>
      <span>{message}</span>
    </section>
  );
}
