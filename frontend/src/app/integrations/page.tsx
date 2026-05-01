"use client";

import {
  Bot,
  Calendar,
  CheckCircle2,
  Database,
  ExternalLink,
  KeyRound,
  LockKeyhole,
  Mail,
  MessageSquare,
  PlugZap,
  Radio,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useJobStatus } from "@/hooks/useJobStatus";
import { apiGet, apiPost } from "@/lib/api/client";
import type {
  AgentReviewResponse,
  GoogleRuntimeStatus,
  IntegrationConnection,
  IntegrationManifest,
  IntegrationSyncResponse,
  OAuthInstallUrlResponse,
  SlackRuntimeStatus,
} from "@/lib/api/types";

const GOOGLE_CONNECTOR_TYPES = ["gmail", "drive", "calendar"] as const;

const integrationVisuals = {
  slack: {
    icon: MessageSquare,
    accent: "bg-[#21132b] text-white",
    description: "채널 메시지를 수집해 타임라인, 히스토리, 결정 후보를 만듭니다.",
    agentAction: {
      key: "slack",
      label: "Slack Agent 실행",
      runningLabel: "Slack Agent 실행 중",
      path: "/api/v1/integrations/slack/agent-review",
    },
  },
  gmail: {
    icon: Mail,
    accent: "bg-blue-50 text-blue-700",
    description: "메일 흐름을 요약하고 결정, 후속 작업, 히스토리 후보를 추출합니다.",
    agentAction: {
      key: "mail-docs",
      label: "Mail/Docs Agent 실행",
      runningLabel: "Mail/Docs Agent 실행 중",
      path: "/api/v1/integrations/mail-docs/agent-review",
    },
  },
  drive: {
    icon: Database,
    accent: "bg-emerald-50 text-emerald-700",
    description: "사내 문서와 버전 정보를 회사 메모리의 근거로 연결합니다.",
    agentAction: {
      key: "mail-docs",
      label: "Mail/Docs Agent 실행",
      runningLabel: "Mail/Docs Agent 실행 중",
      path: "/api/v1/integrations/mail-docs/agent-review",
    },
  },
  calendar: {
    icon: Calendar,
    accent: "bg-amber-50 text-amber-700",
    description: "회의 일정과 시간 맥락을 히스토리 이벤트의 타임라인 근거로 사용합니다.",
    agentAction: undefined,
  },
} satisfies Record<
  string,
  {
    icon: typeof MessageSquare;
    accent: string;
    description: string;
    agentAction?: {
      key: string;
      label: string;
      runningLabel: string;
      path: string;
    };
  }
>;

const fallbackVisual = {
  icon: PlugZap,
  accent: "bg-neutral-100 text-neutral-700",
  description: "공통 ingestion contract를 통해 회사 메모리로 연결됩니다.",
  agentAction: undefined,
};

export default function IntegrationsPage() {
  const [manifests, setManifests] = useState<IntegrationManifest[]>([]);
  const [activeJobId, setActiveJobId] = useState<string>();
  const [syncResult, setSyncResult] = useState<IntegrationSyncResponse>();
  const [agentResult, setAgentResult] = useState<AgentReviewResponse>();
  const [connections, setConnections] = useState<IntegrationConnection[]>([]);
  const [slackRuntime, setSlackRuntime] = useState<SlackRuntimeStatus>();
  const [googleRuntimeByType, setGoogleRuntimeByType] = useState<Record<string, GoogleRuntimeStatus>>({});
  const [slackOAuth, setSlackOAuth] = useState<OAuthInstallUrlResponse>();
  const [googleOAuthByType, setGoogleOAuthByType] = useState<Record<string, OAuthInstallUrlResponse>>({});
  const [pendingType, setPendingType] = useState<string>();
  const [agentRunningKey, setAgentRunningKey] = useState<string>();
  const [error, setError] = useState<string>();
  const jobStatus = useJobStatus(activeJobId);

  useEffect(() => {
    let active = true;
    apiGet<IntegrationManifest[]>("/api/v1/integrations")
      .then((manifestResult) => {
        if (active) {
          setManifests(manifestResult);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "연동 정보를 불러오지 못했습니다.");
        }
      });

    apiGet<IntegrationConnection[]>("/api/v1/integrations/connections")
      .then((connectionResult) => {
        if (active) {
          setConnections(connectionResult);
        }
      })
      .catch(() => {
        if (active) {
          setConnections([]);
        }
      });

    apiGet<OAuthInstallUrlResponse>("/api/v1/integrations/slack/oauth/install-url")
      .then((slackOAuthResult) => {
        if (active) {
          setSlackOAuth(slackOAuthResult);
        }
      })
      .catch(() => {
        if (active) {
          setSlackOAuth({
            connector_type: "slack",
            configured: false,
            install_url: null,
            state: null,
            required_scopes: [],
          });
        }
      });

    apiGet<SlackRuntimeStatus>("/api/v1/integrations/slack/runtime-status")
      .then((status) => {
        if (active) {
          setSlackRuntime(status);
        }
      })
      .catch(() => {
        if (active) {
          setSlackRuntime(undefined);
        }
      });

    GOOGLE_CONNECTOR_TYPES.forEach((connectorType) => {
      apiGet<OAuthInstallUrlResponse>(`/api/v1/integrations/${connectorType}/oauth/install-url`)
        .then((googleOAuthResult) => {
          if (active) {
            setGoogleOAuthByType((current) => ({
              ...current,
              [connectorType]: googleOAuthResult,
            }));
          }
        })
        .catch(() => {
          if (active) {
            setGoogleOAuthByType((current) => ({
              ...current,
              [connectorType]: {
                connector_type: connectorType,
                configured: false,
                install_url: null,
                state: null,
                required_scopes: [],
              },
            }));
          }
        });

      apiGet<GoogleRuntimeStatus>(`/api/v1/integrations/${connectorType}/runtime-status`)
        .then((runtimeStatus) => {
          if (active) {
            setGoogleRuntimeByType((current) => ({
              ...current,
              [connectorType]: runtimeStatus,
            }));
          }
        })
        .catch(() => {
          if (active) {
            setGoogleRuntimeByType((current) => {
              const next = { ...current };
              delete next[connectorType];
              return next;
            });
          }
        });
    });

    return () => {
      active = false;
    };
  }, []);

  const visibleManifests = useMemo(
    () =>
      manifests.length > 0
        ? manifests
        : [
            {
              type: "slack",
              display_name: "Slack",
              mode: "mock",
              status: "loading",
              auth_type: "oauth",
              required_scopes: [],
              sync_strategy: "incremental",
              cost_policy: "변경된 원천 데이터만 처리합니다.",
            },
          ],
    [manifests],
  );

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

  async function runAgent(agentKey: string, path: string) {
    setAgentRunningKey(agentKey);
    setError(undefined);

    try {
      const result = await apiPost<AgentReviewResponse>(path);
      setAgentResult(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent 실행에 실패했습니다.");
    } finally {
      setAgentRunningKey(undefined);
    }
  }

  function startOAuth(displayName: string, oauth?: OAuthInstallUrlResponse) {
    if (!oauth?.install_url) {
      setError(`${displayName} OAuth 설정이 아직 준비되지 않았습니다. .env의 client id와 redirect URI를 확인하세요.`);
      return;
    }

    window.location.assign(oauth.install_url);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Tools</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">연동과 에이전트 도구</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Slack, 메일, 문서, 캘린더 데이터를 공통 ingestion contract로 받아 Review Queue와 RAG 흐름에 연결합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <PlugZap className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          Connector contract ready
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-4 sm:grid-cols-2">
          {visibleManifests.map((manifest) => {
            const visual = integrationVisuals[manifest.type as keyof typeof integrationVisuals] ?? fallbackVisual;
            const Icon = visual.icon;
            const pending = pendingType === manifest.type;
            const featured = manifest.type === "slack";
            const agentAction = visual.agentAction;
            const agentRunning = agentAction ? agentRunningKey === agentAction.key : false;
            const connection = connections.find((item) => item.connector_type === manifest.type);
            const credentialAvailable = connection?.credential_status === "available";
            const oauthInstall = manifest.type === "slack" ? slackOAuth : googleOAuthByType[manifest.type];
            const canStartOAuth = Boolean(oauthInstall?.configured && (!connection || !credentialAvailable));
            const showOAuthStatus = manifest.auth_type === "oauth";
            const oauthTheme =
              manifest.type === "slack"
                ? {
                    border: "border-[#e8deef]",
                    bg: "bg-[#fbf8fd]",
                    icon: "text-[#611f69]",
                    text: "text-[#21132b]",
                    pill: "text-[#611f69]",
                    button: "border-[#611f69] text-[#611f69] hover:bg-[#fbf8fd]",
                  }
                : {
                    border: "border-blue-100",
                    bg: "bg-blue-50/70",
                    icon: "text-blue-700",
                    text: "text-blue-950",
                    pill: "text-blue-700",
                    button: "border-blue-600 text-blue-700 hover:bg-blue-50",
                  };
            return (
              <article
                key={manifest.type}
                className={`rounded-lg border bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                  featured ? "border-[#c9b7d5]" : "border-[var(--line-soft)]"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${visual.accent}`}>
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold">{manifest.display_name}</h3>
                        {featured ? (
                          <span className="rounded-full bg-[var(--workspace-accent)] px-2 py-0.5 text-xs font-bold text-[#13231f]">
                            우선순위
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs font-semibold text-[var(--workspace-rail-active)]">
                        {manifest.mode} · {manifest.sync_strategy}
                      </p>
                    </div>
                  </div>
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" aria-hidden="true" />
                </div>

                <p className="mt-4 min-h-12 text-sm leading-6 text-[var(--ink-muted)]">{visual.description}</p>

                <div className="mt-3 grid gap-2 text-xs text-[var(--ink-muted)]">
                  <div className="flex items-center gap-2">
                    <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
                    {manifest.auth_type.toUpperCase()} · {formatScopes(manifest.required_scopes)}
                  </div>
                  <div className="flex items-start gap-2">
                    <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{manifest.cost_policy}</span>
                  </div>
                </div>

                {showOAuthStatus ? (
                  <div
                    data-testid={`${manifest.type}-oauth-status`}
                    className={`mt-4 rounded-lg border ${oauthTheme.border} ${oauthTheme.bg} p-3 text-sm`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <LockKeyhole className={`h-4 w-4 shrink-0 ${oauthTheme.icon}`} aria-hidden="true" />
                        <span
                          data-testid={`${manifest.type}-oauth-workspace-name`}
                          className={`truncate font-semibold ${oauthTheme.text}`}
                        >
                          {connection
                            ? connection.workspace_name
                            : oauthInstall?.configured
                              ? `${manifest.display_name} 연결 필요`
                              : "OAuth 설정 필요"}
                        </span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className={`rounded-full bg-white px-2 py-0.5 text-xs font-semibold ${oauthTheme.pill}`}>
                          {connection ? (credentialAvailable ? connection.status : "token missing") : "ready"}
                        </span>
                        {canStartOAuth ? (
                          <button
                            type="button"
                            onClick={() => startOAuth(manifest.display_name, oauthInstall)}
                            className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border bg-white px-2.5 text-xs font-semibold shadow-sm ${oauthTheme.button}`}
                          >
                            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                            {connection ? `${manifest.display_name} 재연결` : `${manifest.display_name} 연결`}
                          </button>
                        ) : null}
                      </div>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
                      {connection
                        ? credentialAvailable
                          ? `권한 ${connection.scopes.length.toLocaleString()}개 확인됨 · ${connection.masked_bot_token}`
                          : `권한 ${connection.scopes.length.toLocaleString()}개 확인됨 · backend 재시작으로 개발 vault 토큰이 비어 있어 재연결이 필요합니다.`
                        : oauthInstall?.configured
                          ? `${manifest.display_name} 설치 URL이 준비되었습니다. 설치 후에도 동기화는 변경분만 가져옵니다.`
                          : "환경 변수 설정 전까지는 mock 데이터로 안전하게 시연합니다."}
                    </p>
                  </div>
                ) : null}

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line-soft)] pt-4">
                  <span className="text-xs text-[var(--ink-muted)]">
                    {manifest.mode === "mock" ? "현재 mock 데이터 사용" : "실제 OAuth 연동"}
                  </span>
                  <div data-testid={`${manifest.type}-card-actions`} className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void startSync(manifest.type)}
                      disabled={Boolean(pendingType)}
                      className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-neutral-300 disabled:bg-neutral-300"
                    >
                      <RefreshCw className="h-4 w-4" aria-hidden="true" />
                      {pending ? "동기화 중" : "동기화"}
                    </button>
                    {agentAction ? (
                      <button
                        type="button"
                        onClick={() => void runAgent(agentAction.key, agentAction.path)}
                        disabled={agentRunning}
                        className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 text-sm font-semibold text-[#21132b] shadow-sm hover:bg-[#fbfaf8] disabled:cursor-not-allowed disabled:text-neutral-400"
                      >
                        <Bot className="h-4 w-4" aria-hidden="true" />
                        {agentRunning ? agentAction.runningLabel : agentAction.label}
                      </button>
                    ) : null}
                  </div>
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

          <div className="space-y-3 p-4">
            {slackRuntime ? <SlackRuntimeStatusPanel status={slackRuntime} /> : null}
            <GoogleRuntimeStatusList statuses={googleRuntimeByType} />

            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
            ) : null}

            {agentResult ? (
              <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-800">
                <p className="font-semibold">{formatAgentName(agentResult.agent_name)} 완료</p>
                <p className="mt-1">Review Queue 후보 {agentResult.created_review_items}개를 생성했습니다.</p>
              </div>
            ) : null}

            {syncResult ? (
              <div className="space-y-3 text-sm">
                <div className="rounded-lg bg-[#fbfaf8] p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">Job</p>
                  <p className="mt-1 break-all font-medium">{syncResult.job_id}</p>
                </div>
                <div className="grid grid-cols-2 gap-3" data-testid="sync-result-metrics">
                  <ResultMetric label="Fetched" value={syncResult.fetched_events} />
                  <ResultMetric label="Review items" value={syncResult.created_review_items} />
                  <ResultMetric label="Skipped" value={syncResult.skipped_events} />
                  <ResultMetric label="Status" value={syncResult.status} />
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
                왼쪽 도구에서 동기화를 실행하면 작업 스트림과 생성된 Review 후보 수를 확인할 수 있습니다.
              </div>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}

function ResultMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-[#fbfaf8] p-3">
      <p className="text-xs text-[var(--ink-muted)]">{label}</p>
      <p className="mt-1 font-semibold">{typeof value === "number" ? value.toLocaleString() : value}</p>
    </div>
  );
}

function SlackRuntimeStatusPanel({ status }: { status: SlackRuntimeStatus }) {
  const channelLabel =
    status.configured_channel_ids.length > 0 ? status.configured_channel_ids.join(", ") : "채널 미설정";
  const latestSync = status.latest_sync;

  return (
    <div data-testid="slack-runtime-status" className="rounded-lg border border-[#e8deef] bg-[#fbf8fd] p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-[#21132b]">Slack 운영 상태</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            상태 조회는 sync나 LLM 호출을 실행하지 않습니다.
          </p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-[#611f69]">
          {status.mode}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs">
        <div className="flex items-center justify-between gap-3 rounded-md bg-white px-2 py-2">
          <span className="text-[var(--ink-muted)]">채널</span>
          <span className="max-w-[210px] truncate font-semibold">{channelLabel}</span>
        </div>
        <div className="flex items-center justify-between gap-3 rounded-md bg-white px-2 py-2">
          <span className="text-[var(--ink-muted)]">연결</span>
          <span className="font-semibold">{status.connection_status}</span>
        </div>
        <div className="flex items-center justify-between gap-3 rounded-md bg-white px-2 py-2">
          <span className="text-[var(--ink-muted)]">자격 증명</span>
          <span className="font-semibold">{status.credential_status}</span>
        </div>
      </div>
      {latestSync ? (
        <div className="mt-3 rounded-md bg-white px-2 py-2 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="font-semibold">최근 sync</span>
            <span className="font-semibold">{latestSync.status}</span>
          </div>
          <p className="mt-1 truncate text-[var(--ink-muted)]">{latestSync.message}</p>
        </div>
      ) : null}
    </div>
  );
}

function GoogleRuntimeStatusList({ statuses }: { statuses: Record<string, GoogleRuntimeStatus> }) {
  const rows = GOOGLE_CONNECTOR_TYPES.map((connectorType) => statuses[connectorType]).filter(Boolean);
  if (rows.length === 0) {
    return null;
  }

  return (
    <div data-testid="google-runtime-status" className="rounded-lg border border-blue-100 bg-blue-50/70 p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-blue-950">Google 운영 상태</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">Gmail, Drive, Calendar 상태를 한 번에 확인합니다.</p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-blue-700">
          {rows[0]?.mode ?? "mock"}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.map((status) => (
          <div key={status.connector_type} className="rounded-md bg-white px-2 py-2 text-xs">
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold">{formatConnectorName(status.connector_type)}</span>
              <span className="font-semibold">{status.connection_status}</span>
            </div>
            <div className="mt-1 flex items-center justify-between gap-3 text-[var(--ink-muted)]">
              <span className="max-w-[180px] truncate">{status.account_name ?? "계정 미연결"}</span>
              <span>{status.credential_status}</span>
            </div>
            {status.latest_sync ? (
              <p className="mt-1 truncate text-[var(--ink-muted)]">
                최근 sync: {status.latest_sync.status} · {status.latest_sync.message}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatScopes(scopes: string[]) {
  if (scopes.length === 0) {
    return "scope 준비 중";
  }
  if (scopes.length <= 2) {
    return scopes.join(", ");
  }
  return `${scopes[0]}, ${scopes[1]} 외 ${scopes.length - 2}개`;
}

function formatAgentName(agentName: string) {
  if (agentName === "slack_agent") {
    return "Slack Agent";
  }
  if (agentName === "mail_document_agent") {
    return "Mail/Docs Agent";
  }
  return agentName;
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
