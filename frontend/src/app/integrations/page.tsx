"use client";

import {
  ArrowRight,
  Bot,
  Calendar,
  CheckCircle2,
  Database,
  ExternalLink,
  FileText,
  KeyRound,
  LockKeyhole,
  Mail,
  MessageSquare,
  PlugZap,
  Radio,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useJobStatus } from "@/hooks/useJobStatus";
import { apiGet, apiPost, apiDelete } from "@/lib/api/client";
import { notifyReviewQueueUpdated } from "@/lib/reviewQueueEvents";
import type {
  AgentReviewResponse,
  AgentLlmPreflight,
  GoogleRuntimeStatus,
  IntegrationConnection,
  IntegrationManifest,
  IntegrationSyncResponse,
  OAuthInstallUrlResponse,
  SlackRuntimeStatus,
  DashboardResponse,
} from "@/lib/api/types";

const GOOGLE_CONNECTOR_TYPES = ["gmail", "drive", "calendar"] as const;
const SYNC_RUNNING_STAGES = [
  "원본 수집과 AI 분석을 진행 중입니다.",
  "프로젝트 분류와 검토 후보를 정리하고 있습니다.",
  "검토 항목을 저장하고 화면에 반영하고 있습니다.",
] as const;
const SYNC_STATUS_POLL_INTERVAL_MS = 1500;
const SYNC_STATUS_MAX_POLLS = 90;
const LOST_RESPONSE_RECOVERY_POLLS = 60;
const SYNC_BACKGROUND_NOTICE_DELAY_MS = 120_000;
const BACKGROUND_SYNC_CONTINUES_MESSAGE =
  "백그라운드에서 계속 진행 중입니다. 완료되면 작업 스트림의 최근 sync 상태에 반영됩니다.";

type SyncProgressState = {
  connectorType: string;
  displayName: string;
  status: "running" | "complete" | "error";
  stageIndex: number;
  progressPct: number;
  backgrounded: boolean;
  jobId?: string;
  lastMessage?: string;
  result?: IntegrationSyncResponse;
  errorMessage?: string;
};

type IntegrationRuntimeStatus = SlackRuntimeStatus | GoogleRuntimeStatus;

/**
 * 연동 도구별 시각적 요소(아이콘, 색상, 설명 등) 정의
 */
const integrationVisuals = {
  slack: {
    icon: MessageSquare,
    accent: "bg-[#21132b] text-white",
    description: "채널 메시지를 수집해 타임라인, 히스토리, 결정 후보를 만듭니다.",
  },
  gmail: {
    icon: Mail,
    accent: "bg-blue-50 text-blue-700",
    description: "메일 흐름을 요약하고 결정, 후속 작업, 히스토리 후보를 추출합니다.",
  },
  drive: {
    icon: Database,
    accent: "bg-emerald-50 text-emerald-700",
    description: "사내 문서와 버전 정보를 회사 메모리의 근거로 연결합니다.",
  },
  calendar: {
    icon: Calendar,
    accent: "bg-amber-50 text-amber-700",
    description: "회의 일정과 시간 맥락을 히스토리 이벤트의 타임라인 근거로 사용합니다.",
  },
} satisfies Record<
  string,
  {
    icon: typeof MessageSquare;
    accent: string;
    description: string;
  }
>;

/**
 * 정의되지 않은 연동 도구에 대한 기본 시각적 설정
 */
const fallbackVisual = {
  icon: PlugZap,
  accent: "bg-neutral-100 text-neutral-700",
  description: "공통 ingestion contract를 통해 회사 메모리로 연결됩니다.",
};

/**
 * 연동 관리 페이지 컴포넌트
 */
function sleep(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms));
}

function stageIndexFromProgress(progressPct?: number) {
  if (progressPct === undefined || progressPct < 50) {
    return 0;
  }
  if (progressPct < 90) {
    return 1;
  }
  return 2;
}

function countFromSyncMessage(message: string | undefined, key: string) {
  const match = (message ?? "").match(new RegExp(`${key}=(\\d+)`));
  return match ? Number.parseInt(match[1], 10) : undefined;
}

function runtimeJobMatches(
  runtime: IntegrationRuntimeStatus,
  startedAtMs: number,
  jobId?: string,
) {
  const latest = runtime.latest_sync;
  if (!latest) {
    return false;
  }
  if (jobId) {
    return latest.job_id === jobId;
  }

  const timestamp = latest.updated_at ?? latest.created_at;
  if (!timestamp) {
    return false;
  }
  const timestampMs = new Date(timestamp).getTime();
  return Number.isFinite(timestampMs) && timestampMs >= startedAtMs - 5000;
}

function shouldRecoverLostSyncResponse(message: string) {
  return /internal server error|socket|network|failed to fetch|request failed with 5/i.test(message);
}

function isBackgroundSyncContinuation(message: string) {
  return message.includes("백그라운드에서 계속 진행 중입니다");
}

function syncResponseFromRuntimeStatus(
  connectorType: string,
  runtime: IntegrationRuntimeStatus,
  fallback?: IntegrationSyncResponse,
): IntegrationSyncResponse | undefined {
  const latest = runtime.latest_sync;
  if (!latest) {
    return undefined;
  }

  const message = latest.message ?? "";
  const slackSummary =
    runtime.connector_type === "slack" ? runtime.latest_sync_summary : undefined;
  const pendingReviewCount =
    runtime.connector_type === "slack"
      ? (countFromSyncMessage(message, "pending_review_items") ?? runtime.agent_bridge.pending_review_count)
      : (countFromSyncMessage(message, "pending_review_items") ?? fallback?.pending_review_count ?? 0);

  return {
    job_id: latest.job_id,
    connector_type: connectorType,
    status: latest.status,
    created_review_items:
      slackSummary?.created_review_items ??
      countFromSyncMessage(message, "created_review_items") ??
      fallback?.created_review_items ??
      0,
    pending_review_count: pendingReviewCount,
    fetched_events:
      slackSummary?.fetched_events ??
      countFromSyncMessage(message, "fetched") ??
      fallback?.fetched_events ??
      0,
    skipped_events:
      slackSummary?.skipped_events ??
      countFromSyncMessage(message, "skipped_events") ??
      fallback?.skipped_events ??
      0,
    parser_status_counts: fallback?.parser_status_counts ?? {},
    changed_source_ids: fallback?.changed_source_ids ?? [],
    agent_generated_items: fallback?.agent_generated_items ?? 0,
    project_assignment_items: fallback?.project_assignment_items ?? 0,
  };
}

export default function IntegrationsPage() {
  const [manifests, setManifests] = useState<IntegrationManifest[]>([]);
  const [activeJobId, setActiveJobId] = useState<string>();
  const [syncResult, setSyncResult] = useState<IntegrationSyncResponse>();
  const [agentResult, setAgentResult] = useState<AgentReviewResponse>();
  const [connections, setConnections] = useState<IntegrationConnection[]>([]);
  const [slackRuntime, setSlackRuntime] = useState<SlackRuntimeStatus>();
  const [slackLlmPreflight, setSlackLlmPreflight] = useState<AgentLlmPreflight>();
  const [mailDocsLlmPreflight, setMailDocsLlmPreflight] = useState<AgentLlmPreflight>();
  const [selectedSlackChannels, setSelectedSlackChannels] = useState<string[]>([]);
  const [googleRuntimeByType, setGoogleRuntimeByType] = useState<Record<string, GoogleRuntimeStatus>>({});
  const [dashboardSummary, setDashboardSummary] = useState<DashboardResponse>();
  const [slackOAuth, setSlackOAuth] = useState<OAuthInstallUrlResponse>();
  const [googleOAuthByType, setGoogleOAuthByType] = useState<Record<string, OAuthInstallUrlResponse>>({});
  const [pendingType, setPendingType] = useState<string>();
  const [syncProgress, setSyncProgress] = useState<SyncProgressState>();
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [llmAgentRunning, setLlmAgentRunning] = useState(false);
  const [mailDocsLlmAgentRunning, setMailDocsLlmAgentRunning] = useState(false);
  const [error, setError] = useState<string>();
  const jobStatus = useJobStatus(activeJobId);

  // 초기 로드 시 다양한 연동 정보 및 상태 조회
  useEffect(() => {
    let active = true;
    
    // 연동 가능한 커넥터 목록(Manifest) 조회
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

    // 현재 활성화된 연결(Credentials/Token 상태 등) 조회
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

    // 대시보드 요약 정보(소스별 카운트 등) 조회
    apiGet<DashboardResponse>("/api/v1/dashboard")
      .then((summary) => {
        if (active) {
          setDashboardSummary(summary);
        }
      })
      .catch(() => {
        if (active) {
          setDashboardSummary(undefined);
        }
      });

    // Slack OAuth 설치 URL 조회
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

    // Slack 운영 상태(채널 선택 등) 조회
    apiGet<SlackRuntimeStatus>("/api/v1/integrations/slack/runtime-status")
      .then((status) => {
        if (active) {
          setSlackRuntime(status);
          setSelectedSlackChannels(status.selected_channel_ids);
        }
      })
      .catch(() => {
        if (active) {
          setSlackRuntime(undefined);
        }
      });

    // Slack LLM 에이전트 실행 전 검사(예산, 모델 등)
    apiGet<AgentLlmPreflight>("/api/v1/integrations/slack/agent-review/llm/preflight")
      .then((preflight) => {
        if (active) {
          setSlackLlmPreflight(preflight);
        }
      })
      .catch(() => {
        if (active) {
          setSlackLlmPreflight(undefined);
        }
      });

    apiGet<AgentLlmPreflight>("/api/v1/integrations/mail-docs/agent-review/llm/preflight")
      .then((preflight) => {
        if (active) {
          setMailDocsLlmPreflight(preflight);
        }
      })
      .catch(() => {
        if (active) {
          setMailDocsLlmPreflight(undefined);
        }
      });

    // Google 커넥터들(Gmail, Drive, Calendar)의 OAuth 및 상태 조회
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

  useEffect(() => {
    if (syncProgress?.status !== "running") {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setSyncProgress((current) => {
        if (!current || current.status !== "running") {
          return current;
        }
        return {
          ...current,
          stageIndex: Math.min(current.stageIndex + 1, SYNC_RUNNING_STAGES.length - 1),
        };
      });
    }, 7000);

    return () => window.clearInterval(timer);
  }, [syncProgress?.connectorType, syncProgress?.status]);


  async function refreshDashboardSummary() {
    try {
      const summary = await apiGet<DashboardResponse>("/api/v1/dashboard");
      setDashboardSummary(summary);
      notifyReviewQueueUpdated();
    } catch {
      setDashboardSummary(undefined);
    }
  }

  async function refreshRuntimeAfterMutation(type: string) {
    if (type === "slack") {
      try {
        const status = await apiGet<SlackRuntimeStatus>("/api/v1/integrations/slack/runtime-status");
        setSlackRuntime(status);
      } catch {
        setSlackRuntime(undefined);
      }
    }

    if (GOOGLE_CONNECTOR_TYPES.includes(type as (typeof GOOGLE_CONNECTOR_TYPES)[number])) {
      try {
        const status = await apiGet<GoogleRuntimeStatus>(`/api/v1/integrations/${type}/runtime-status`);
        setGoogleRuntimeByType((current) => ({ ...current, [type]: status }));
      } catch {
        setGoogleRuntimeByType((current) => {
          const next = { ...current };
          delete next[type];
          return next;
        });
      }
    }

    await refreshDashboardSummary();
  }

  async function loadRuntimeStatus(type: string): Promise<IntegrationRuntimeStatus | undefined> {
    if (type === "slack") {
      const status = await apiGet<SlackRuntimeStatus>("/api/v1/integrations/slack/runtime-status");
      setSlackRuntime(status);
      return status;
    }

    if (GOOGLE_CONNECTOR_TYPES.includes(type as (typeof GOOGLE_CONNECTOR_TYPES)[number])) {
      const status = await apiGet<GoogleRuntimeStatus>(`/api/v1/integrations/${type}/runtime-status`);
      setGoogleRuntimeByType((current) => ({ ...current, [type]: status }));
      return status;
    }

    return undefined;
  }

  async function waitForSyncCompletion(
    type: string,
    jobId: string,
    fallback: IntegrationSyncResponse,
  ): Promise<IntegrationSyncResponse> {
    for (let attempt = 0; attempt < SYNC_STATUS_MAX_POLLS; attempt += 1) {
      const runtime = await loadRuntimeStatus(type).catch(() => undefined);
      if (runtime?.latest_sync && runtimeJobMatches(runtime, Date.now(), jobId)) {
        const latest = runtime.latest_sync;
        setSyncProgress((current) =>
          current?.connectorType === type && current.status === "running"
            ? {
                ...current,
                stageIndex: stageIndexFromProgress(latest.progress_pct),
                progressPct: latest.progress_pct,
                jobId: latest.job_id,
                lastMessage: latest.message,
              }
            : current,
        );

        if (latest.status === "failed") {
          throw new Error(latest.message || "동기화 작업이 실패했습니다.");
        }
        if (latest.status === "complete") {
          return syncResponseFromRuntimeStatus(type, runtime, fallback) ?? fallback;
        }
      }
      await sleep(SYNC_STATUS_POLL_INTERVAL_MS);
    }

    throw new Error("동기화 작업이 백그라운드에서 계속 진행 중입니다. 잠시 후 작업 스트림을 확인해 주세요.");
  }

  async function recoverCompletedSyncAfterLostResponse(
    type: string,
    startedAtMs: number,
  ): Promise<IntegrationSyncResponse | undefined> {
    for (let attempt = 0; attempt < LOST_RESPONSE_RECOVERY_POLLS; attempt += 1) {
      const runtime = await loadRuntimeStatus(type).catch(() => undefined);
      if (runtime?.latest_sync && runtimeJobMatches(runtime, startedAtMs)) {
        const latest = runtime.latest_sync;
        setSyncProgress((current) =>
          current?.connectorType === type && current.status === "running"
            ? {
                ...current,
                stageIndex: stageIndexFromProgress(latest.progress_pct),
                progressPct: latest.progress_pct,
                jobId: latest.job_id,
                lastMessage: latest.message,
              }
            : current,
        );

        if (latest.status === "failed") {
          throw new Error(latest.message || "동기화 작업이 실패했습니다.");
        }
        if (latest.status === "complete") {
          return syncResponseFromRuntimeStatus(type, runtime);
        }
      }
      await sleep(SYNC_STATUS_POLL_INTERVAL_MS);
    }

    return undefined;
  }

  async function markSyncComplete(type: string, result: IntegrationSyncResponse) {
    setSyncResult(result);
    setActiveJobId(result.job_id);
    setSyncProgress((current) =>
      current?.connectorType === type
        ? {
            ...current,
            status: "complete",
            stageIndex: SYNC_RUNNING_STAGES.length - 1,
            progressPct: 100,
            jobId: result.job_id,
            result,
          }
        : current,
    );
    await refreshRuntimeAfterMutation(type);
  }

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

  /**
   * 특정 커넥터의 데이터 동기화(Sync)를 시작합니다.
   */
  async function startSync(type: string) {
    const displayName = connectorDisplayName(type, manifests);
    const startedAtMs = Date.now();
    setPendingType(type);
    setError(undefined);
    setSyncProgress({
      connectorType: type,
      displayName,
      status: "running",
      stageIndex: 0,
      progressPct: 0,
      backgrounded: false,
    });
    setSyncModalOpen(true);
    const backgroundNoticeTimer = window.setTimeout(() => {
      setSyncProgress((current) =>
        current?.connectorType === type && current.status === "running"
          ? {
              ...current,
              backgrounded: true,
              errorMessage: BACKGROUND_SYNC_CONTINUES_MESSAGE,
            }
          : current,
      );
    }, SYNC_BACKGROUND_NOTICE_DELAY_MS);

    try {
      const result = await apiPost<IntegrationSyncResponse>(
        `/api/v1/integrations/${type}/sync`,
        type === "slack" ? { selected_channel_ids: selectedSlackChannels, run_async: true } : undefined,
      );
      setActiveJobId(result.job_id);
      setSyncProgress((current) =>
        current?.connectorType === type
          ? {
              ...current,
              jobId: result.job_id,
              progressPct: result.status === "complete" ? 100 : current.progressPct,
            }
          : current,
      );
      if (result.status === "failed") {
        throw new Error("동기화 작업이 실패했습니다.");
      }
      const completedResult =
        result.status === "complete"
          ? result
          : await waitForSyncCompletion(type, result.job_id, result);
      await markSyncComplete(type, completedResult);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "동기화에 실패했습니다.";
      if (shouldRecoverLostSyncResponse(message)) {
        try {
          const recovered = await recoverCompletedSyncAfterLostResponse(type, startedAtMs);
          if (recovered) {
            setError(undefined);
            await markSyncComplete(type, recovered);
            return;
          }
        } catch (recoveryError) {
          const recoveryMessage =
            recoveryError instanceof Error
              ? recoveryError.message
              : "동기화 작업 상태 확인에 실패했습니다.";
          setError(recoveryMessage);
          setSyncProgress((current) =>
            current?.connectorType === type
              ? {
                  ...current,
                  status: "error",
                  errorMessage: recoveryMessage,
                }
              : current,
          );
          return;
        }
      }
      if (isBackgroundSyncContinuation(message)) {
        setError(undefined);
        setSyncProgress((current) =>
          current?.connectorType === type
            ? {
                ...current,
                status: "running",
                backgrounded: true,
                errorMessage: BACKGROUND_SYNC_CONTINUES_MESSAGE,
              }
            : current,
        );
        return;
      }
      setError(message);
      setSyncProgress((current) =>
        current?.connectorType === type
          ? {
              ...current,
              status: "error",
              errorMessage: message,
            }
          : current,
      );
    } finally {
      window.clearTimeout(backgroundNoticeTimer);
      setPendingType(undefined);
    }
  }

  /**
   * Slack 채널 선택 상태를 토글합니다.
   */
  function toggleSlackChannel(channelId: string) {
    setSelectedSlackChannels((current) => {
      if (current.includes(channelId)) {
        return current.filter((selectedChannelId) => selectedChannelId !== channelId);
      }
      return [...current, channelId];
    });
  }

  async function refreshBackgroundSyncProgress(type: string) {
    const runtime = await loadRuntimeStatus(type).catch(() => undefined);
    const latest = runtime?.latest_sync;
    if (!runtime || !latest) return;
    if (syncProgress?.jobId && latest.job_id !== syncProgress.jobId) return;

    if (latest.status === "complete") {
      const result = syncResponseFromRuntimeStatus(type, runtime, syncProgress?.result);
      if (result) await markSyncComplete(type, result);
      return;
    }

    if (latest.status === "failed") {
      setSyncProgress((current) =>
        current?.connectorType === type
          ? {
              ...current,
              status: "error",
              progressPct: 100,
              stageIndex: SYNC_RUNNING_STAGES.length - 1,
              lastMessage: latest.message,
              errorMessage: latest.message || "동기화 작업이 실패했습니다.",
            }
          : current,
      );
      return;
    }

    setSyncProgress((current) =>
      current?.connectorType === type
        ? {
            ...current,
            status: "running",
            progressPct: latest.progress_pct,
            stageIndex: stageIndexFromProgress(latest.progress_pct),
            jobId: latest.job_id,
            lastMessage: latest.message,
          }
        : current,
    );
  }

  useEffect(() => {
    if (!syncProgress || syncProgress.status !== "running" || !syncProgress.backgrounded) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshBackgroundSyncProgress(syncProgress.connectorType);
    }, SYNC_STATUS_POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [syncProgress?.connectorType, syncProgress?.status, syncProgress?.backgrounded]);

  function openRuntimeSyncProgress(type: string, runtime: IntegrationRuntimeStatus) {
    const latest = runtime.latest_sync;
    if (!latest) return;
    const displayName = connectorDisplayName(type, manifests);
    const isComplete = latest.status === "complete";
    const isError = latest.status === "failed";
    setActiveJobId(latest.job_id);
    setSyncProgress({
      connectorType: type,
      displayName,
      status: isComplete ? "complete" : isError ? "error" : "running",
      stageIndex: stageIndexFromProgress(latest.progress_pct),
      progressPct: latest.progress_pct,
      backgrounded: false,
      jobId: latest.job_id,
      lastMessage: latest.message,
      errorMessage: isError ? latest.message : undefined,
      result: isComplete ? syncResponseFromRuntimeStatus(type, runtime) : undefined,
    });
    setSyncModalOpen(true);
  }

  /**
   * 연동 해제(Disconnect)를 실행합니다.
   */
  async function disconnect(type: string) {
    if (!confirm(`${type} 연동을 해제하시겠습니까? 관련 자격 증명이 삭제됩니다.`)) {
      return;
    }

    setError(undefined);
    try {
      await apiDelete(`/api/v1/integrations/${type}`);
      
      // 연결 목록 갱신
      const connectionResult = await apiGet<IntegrationConnection[]>("/api/v1/integrations/connections");
      setConnections(connectionResult);
      
      // 구글 런타임 상태 갱신
      if (GOOGLE_CONNECTOR_TYPES.includes(type as (typeof GOOGLE_CONNECTOR_TYPES)[number])) {
        setGoogleRuntimeByType((current) => {
          const next = { ...current };
          delete next[type];
          return next;
        });
      }
      
      // 슬랙 런타임 상태 갱신
      if (type === "slack") {
        setSlackRuntime(undefined);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "연동 해제에 실패했습니다.");
    }
  }

  /**
   * Slack LLM 에이전트(비용이 발생하는 실제 LLM 호출)를 실행합니다.
   */
  async function runSlackLlmAgent() {
    setLlmAgentRunning(true);
    setError(undefined);

    try {
      const result = await apiPost<AgentReviewResponse>("/api/v1/integrations/slack/agent-review/llm", {
        confirm_paid_run: true,
      });
      setAgentResult(result);
      setSlackLlmPreflight(result.preflight);
      await refreshDashboardSummary();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "실제 LLM Agent 실행에 실패했습니다.");
    } finally {
      setLlmAgentRunning(false);
    }
  }

  async function runMailDocsLlmAgent() {
    setMailDocsLlmAgentRunning(true);
    setError(undefined);

    try {
      const result = await apiPost<AgentReviewResponse>("/api/v1/integrations/mail-docs/agent-review/llm", {
        confirm_paid_run: true,
      });
      setAgentResult(result);
      setMailDocsLlmPreflight(result.preflight);
      await refreshDashboardSummary();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Mail/Docs LLM Agent 실행에 실패했습니다.");
    } finally {
      setMailDocsLlmAgentRunning(false);
    }
  }

  async function startOAuth(displayName: string, oauth?: OAuthInstallUrlResponse) {
    if (!oauth?.install_url) {
      setError(`${displayName} OAuth 설정이 아직 준비되지 않았습니다. .env의 client id와 redirect URI를 확인하세요.`);
      return;
    }

    if (oauth.install_url === "__direct_connect__") {
      try {
        const connection = await apiPost<IntegrationConnection>("/api/v1/integrations/slack/direct-connect");
        setConnections((current) => {
          const filtered = current.filter((item) => item.connector_type !== "slack");
          return [...filtered, connection];
        });
        
        // 연결 성공 후 런타임 상태 갱신
        apiGet<SlackRuntimeStatus>("/api/v1/integrations/slack/runtime-status")
          .then((status) => {
            setSlackRuntime(status);
            setSelectedSlackChannels(status.selected_channel_ids);
          })
          .catch(() => undefined);
          
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Slack 직접 연결에 실패했습니다.");
      }
      return;
    }

    window.location.assign(oauth.install_url);
  }

  return (
    <div className="reference-dashboard space-y-5">
      {syncProgress && syncModalOpen ? (
        <SyncProgressModal
          progress={syncProgress}
          onBackground={() => {
            setSyncProgress((current) => (current ? { ...current, backgrounded: true } : current));
            setSyncModalOpen(false);
          }}
          onClose={() => setSyncModalOpen(false)}
        />
      ) : null}

      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Tools</p>
          <h1>연동과 에이전트 도구</h1>
          <p>
            Slack, 메일, 문서, 캘린더 데이터를 공통 ingestion contract로 받아 Review Queue와 RAG 흐름에 연결합니다.
          </p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold text-[var(--ink-subtle)]">
          <PlugZap className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          Connector contract ready
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px] items-start">
        <div className="grid gap-4 sm:grid-cols-2 items-start">
          {visibleManifests.map((manifest) => {
            const visual = integrationVisuals[manifest.type as keyof typeof integrationVisuals] ?? fallbackVisual;
            const Icon = visual.icon;
            const pending = pendingType === manifest.type;
            const featured = manifest.type === "slack";
            const connection = connections.find((item) => item.connector_type === manifest.type);
            const credentialAvailable = connection?.credential_status === "available";
            const oauthInstall = manifest.type === "slack" ? slackOAuth : googleOAuthByType[manifest.type];
            const canStartOAuth = Boolean(oauthInstall?.configured && (!connection || !credentialAvailable));
            const showOAuthStatus = manifest.auth_type === "oauth";
            const oauthTheme =
              manifest.type === "slack"
                ? {
                    border: "border-[var(--line-soft)]",
                    bg: "bg-[#fbf8fd]",
                    icon: "text-[var(--workspace-accent)]",
                    text: "text-[var(--ink-strong)]",
                    pill: "text-[var(--ink-strong)]",
                    button: "border-[var(--line-soft)] text-[var(--ink-strong)] hover:bg-[#fbf8fd]",
                  }
                : {
                    border: "border-[var(--line-soft)]",
                    bg: "bg-blue-50/70",
                    icon: "text-[var(--workspace-accent)]",
                    text: "text-[var(--ink-strong)]",
                    pill: "text-[var(--ink-strong)]",
                    button: "border-[var(--line-soft)] text-[var(--ink-strong)] hover:bg-blue-50",
                  };
            return (
              <article
                key={manifest.type}
                className={`integration-glass-card rounded-lg border bg-[var(--glass-elevated)] p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md flex flex-col ${
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
                        <span className={`rounded-full bg-[var(--glass-elevated)] px-2 py-0.5 text-xs font-semibold ${oauthTheme.pill}`}>
                          {connection ? (credentialAvailable ? connection.status : "token missing") : "ready"}
                        </span>
                        {canStartOAuth ? (
                          <button
                            type="button"
                            onClick={() => startOAuth(manifest.display_name, oauthInstall)}
                            className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border bg-[var(--glass-elevated)] px-2.5 text-xs font-semibold shadow-sm ${oauthTheme.button}`}
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

                <div className="mt-auto pt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line-soft)]">
                  <span className="text-xs text-[var(--ink-muted)]">
                    {manifest.mode === "mock" ? "현재 mock 데이터 사용" : "실제 OAuth 연동"}
                  </span>
                  <div data-testid={`${manifest.type}-card-actions`} className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void startSync(manifest.type)}
                      disabled={Boolean(pendingType)}
                      className="liquid-primary inline-flex h-9 items-center justify-center gap-2 rounded-[20px] px-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <RefreshCw className="h-4 w-4" aria-hidden="true" />
                      {pending ? "동기화 중" : "동기화"}
                    </button>
                    {connection ? (
                      <button
                        type="button"
                        onClick={() => void disconnect(manifest.type)}
                        className="liquid-control inline-flex h-9 items-center justify-center gap-2 rounded-[20px] px-3 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-55"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        해제
                      </button>
                    ) : null}
                    {manifest.type === "drive" ? (
                      <a
                        href="/documents"
                        className="liquid-control inline-flex h-9 items-center justify-center gap-1.5 rounded-[20px] px-3 text-sm font-semibold text-[var(--ink-strong)]"
                      >
                        <FileText className="h-4 w-4" aria-hidden="true" />
                        문서 현황 보기 →
                      </a>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
        </div>

        <aside className="integration-glass-card rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] shadow-panel">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-[var(--workspace-rail-active)]" aria-hidden="true" />
              <h3 className="text-sm font-semibold">작업 스트림</h3>
            </div>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">동기화와 Review 후보 생성 상태</p>
          </div>

          <div className="space-y-3 p-4">
            <SourceOperationsPanel summary={dashboardSummary} />

            {syncProgress && !syncModalOpen ? (
              <SyncProgressSummaryCard progress={syncProgress} onOpen={() => setSyncModalOpen(true)} />
            ) : null}

            {!syncProgress && slackRuntime?.latest_sync && ["queued", "running"].includes(slackRuntime.latest_sync.status) ? (
              <RuntimeSyncProgressSummaryCard
                displayName="Slack"
                latest={slackRuntime.latest_sync}
                onOpen={() => openRuntimeSyncProgress("slack", slackRuntime)}
              />
            ) : null}

            {slackRuntime ? (
              <SlackRuntimeStatusPanel
                status={slackRuntime}
                llmPreflight={slackLlmPreflight}
                llmAgentRunning={llmAgentRunning}
                selectedChannelIds={selectedSlackChannels}
                onRunLlmAgent={runSlackLlmAgent}
                onToggleChannel={toggleSlackChannel}
              />
            ) : null}
            <GoogleRuntimeStatusList statuses={googleRuntimeByType} />
            <AgentLlmPreflightPanel
              title="Mail/Docs LLM 테스트"
              preflight={mailDocsLlmPreflight}
              agentRunning={mailDocsLlmAgentRunning}
              onRunAgent={runMailDocsLlmAgent}
            />

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
                <div className="rounded-lg bg-[var(--glass-strong)] p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">Job</p>
                  <p className="mt-1 break-all font-medium">{syncResult.job_id}</p>
                </div>
                <div className="grid grid-cols-2 gap-3" data-testid="sync-result-metrics">
                  <ResultMetric label="Fetched" value={syncResult.fetched_events} />
                  <ResultMetric label="새 검토 항목" value={syncResult.created_review_items} />
                  <ResultMetric label="검토 대기" value={syncResult.pending_review_count} />
                  <ResultMetric label="Skipped" value={syncResult.skipped_events} />
                  <ResultMetric label="Status" value={syncResult.status} />
                </div>
                <ParserQualityBreakdown counts={syncResult.parser_status_counts} />
                <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3">
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
              <div className="rounded-lg border border-dashed border-[var(--line-soft)] bg-[var(--glass-strong)] p-5 text-sm leading-6 text-[var(--ink-muted)]">
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
    <div className="glass-row rounded-lg p-3">
      <p className="text-xs text-[var(--ink-muted)]">{label}</p>
      <p className="mt-1 font-semibold">{typeof value === "number" ? value.toLocaleString() : value}</p>
    </div>
  );
}

function SyncProgressSummaryCard({
  progress,
  onOpen,
}: {
  progress: SyncProgressState;
  onOpen: () => void;
}) {
  const currentStage = SYNC_RUNNING_STAGES[progress.stageIndex] ?? SYNC_RUNNING_STAGES[0];
  const isComplete = progress.status === "complete";
  const isError = progress.status === "error";
  const toneClass = isComplete
    ? "border-emerald-200 bg-emerald-50 text-emerald-950"
    : isError
      ? "border-red-200 bg-red-50 text-red-950"
      : "border-amber-200 bg-amber-50 text-amber-950";
  const subTextClass = isComplete ? "text-emerald-900" : isError ? "text-red-900" : "text-amber-900";
  const title = isComplete
    ? `${progress.displayName} 동기화 완료`
    : isError
      ? `${progress.displayName} 동기화 실패`
      : `${progress.displayName} 동기화 진행 중`;
  return (
    <div
      data-testid="background-sync-progress"
      className={`rounded-lg border p-3 text-sm ${toneClass}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className={`mt-1 text-xs leading-5 ${subTextClass}`}>{currentStage}</p>
        </div>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex h-8 items-center justify-center rounded-lg border border-current bg-white px-3 text-xs font-bold hover:bg-white/70"
        >
          {progress.status === "running" ? "진행 창 열기" : "결과 보기"}
        </button>
      </div>
      <ProgressBar progressPct={progress.progressPct} />
      {progress.lastMessage ? <p className={`mt-2 break-all text-xs ${subTextClass}`}>{progress.lastMessage}</p> : null}
    </div>
  );
}

function RuntimeSyncProgressSummaryCard({
  displayName,
  latest,
  onOpen,
}: {
  displayName: string;
  latest: NonNullable<SlackRuntimeStatus["latest_sync"]>;
  onOpen: () => void;
}) {
  return (
    <div
      data-testid="runtime-sync-progress"
      className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{displayName} 동기화 진행 중</p>
          <p className="mt-1 text-xs leading-5 text-blue-900">
            {SYNC_RUNNING_STAGES[stageIndexFromProgress(latest.progress_pct)]}
          </p>
        </div>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex h-8 items-center justify-center rounded-lg border border-blue-300 bg-white px-3 text-xs font-bold text-blue-950 hover:bg-blue-100"
        >
          진행 창 열기
        </button>
      </div>
      <ProgressBar progressPct={latest.progress_pct} />
      {latest.message ? <p className="mt-2 break-all text-xs text-blue-900">{latest.message}</p> : null}
    </div>
  );
}

function ProgressBar({ progressPct }: { progressPct: number }) {
  const clamped = Math.max(0, Math.min(100, Math.round(progressPct)));
  return (
    <div className="mt-3" data-testid="sync-progress-percent">
      <div className="flex items-center justify-between text-xs font-bold">
        <span>진행률</span>
        <span>{clamped}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/70">
        <div className="h-full rounded-full bg-[var(--workspace-accent)]" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

function SyncProgressModal({
  progress,
  onBackground,
  onClose,
}: {
  progress: SyncProgressState;
  onBackground: () => void;
  onClose: () => void;
}) {
  const isRunning = progress.status === "running";
  const isComplete = progress.status === "complete";
  const isError = progress.status === "error";
  const result = progress.result;

  return (
    <div
      data-testid="sync-progress-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sync-progress-title"
      className="fixed inset-0 z-50 grid place-items-center bg-[#120b18]/72 px-4 backdrop-blur-sm"
    >
      <div
        data-testid="sync-progress-modal"
        className="max-h-[calc(100vh-2rem)] w-full max-w-md overflow-y-auto rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-5 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[var(--glass-strong)] text-[var(--workspace-rail-active)]">
              {isComplete ? (
                <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              ) : (
                <RefreshCw className={`h-5 w-5 ${isRunning ? "animate-spin" : ""}`} aria-hidden="true" />
              )}
            </span>
            <div className="min-w-0">
              <h2 id="sync-progress-title" className="text-base font-semibold text-[var(--ink-strong)]">
                {isComplete
                  ? "동기화 완료"
                  : isError
                    ? `${progress.displayName} 동기화 실패`
                    : `${progress.displayName} 동기화 중`}
              </h2>
              <p data-testid="sync-modal-step" className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">
                {isComplete
                  ? `${progress.displayName} 데이터를 검토 큐에 반영했습니다.`
                  : isError
                    ? (progress.errorMessage ?? "동기화 중 오류가 발생했습니다.")
                    : progress.backgrounded
                      ? (progress.errorMessage ?? BACKGROUND_SYNC_CONTINUES_MESSAGE)
                      : SYNC_RUNNING_STAGES[progress.stageIndex]}
              </p>
            </div>
          </div>

          {!isRunning ? (
            <button
              type="button"
              onClick={onClose}
              className="liquid-control grid h-8 w-8 shrink-0 place-items-center rounded-lg"
              aria-label="모달 닫기"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : null}
        </div>

        <div className="mt-4 grid gap-2 text-sm">
          <SyncStep label="원본 수집" active={isRunning && progress.stageIndex === 0} done={progress.stageIndex > 0 || isComplete} />
          <SyncStep label="AI 분석" active={isRunning && progress.stageIndex === 1} done={progress.stageIndex > 1 || isComplete} />
          <SyncStep label="검토 항목 저장" active={isRunning && progress.stageIndex === 2} done={isComplete} />
        </div>

        <ProgressBar progressPct={progress.progressPct} />
        {progress.lastMessage ? (
          <p className="mt-2 break-all text-xs leading-5 text-[var(--ink-muted)]">{progress.lastMessage}</p>
        ) : null}

        {result ? (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <ResultMetric label="새 검토 항목" value={`${result.created_review_items.toLocaleString()}개`} />
              <ResultMetric label="검토 대기" value={`${result.pending_review_count.toLocaleString()}개`} />
            </div>
            <p className="mt-3 text-sm font-medium text-[var(--ink-strong)]">
              새 검토 항목 {result.created_review_items.toLocaleString()}개, 검토 대기{" "}
              {result.pending_review_count.toLocaleString()}개입니다.
            </p>
          </>
        ) : null}

        <div className="mt-5 grid gap-2 sm:flex sm:flex-wrap sm:justify-end">
          {isRunning ? (
            <button
              type="button"
              onClick={onBackground}
              className="liquid-control inline-flex h-9 w-full items-center justify-center rounded-lg px-3 text-sm font-semibold sm:w-auto"
            >
              백그라운드에서 계속 진행
            </button>
          ) : null}
          {isComplete ? (
            <a
              href="/review"
              className="liquid-primary inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold sm:w-auto"
            >
              검토사항으로 이동
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </a>
          ) : null}
          {!isRunning ? (
            <button
              type="button"
              onClick={onClose}
              className="liquid-control inline-flex h-9 w-full items-center justify-center rounded-lg px-3 text-sm font-semibold sm:w-auto"
            >
              닫기
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SyncStep({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-[var(--glass-strong)] px-3 py-2">
      <span
        className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px] font-bold ${
          done
            ? "bg-emerald-100 text-emerald-700"
            : active
              ? "bg-[var(--workspace-accent)] text-[#13231f]"
              : "bg-[var(--glass-elevated)] text-[var(--ink-muted)]"
        }`}
      >
        {done ? "✓" : active ? "…" : ""}
      </span>
      <span className="font-medium text-[var(--ink-strong)]">{label}</span>
    </div>
  );
}

/**
 * 소스별 데이터 수집 현황을 보여주는 패널 컴포넌트
 */
function SourceOperationsPanel({ summary }: { summary?: DashboardResponse }) {
  const counts = summary?.source_counts ?? {
    slack: 0,
    gmail: 0,
    drive: 0,
    calendar: 0,
    other: 0,
  };
  const total =
    (counts.slack ?? 0) +
    (counts.gmail ?? 0) +
    (counts.drive ?? 0) +
    (counts.calendar ?? 0) +
    (counts.other ?? 0);

  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-[var(--ink-strong)]">소스별 연동 현황</h4>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">수집량과 커넥터별 비중</p>
        </div>
        <span className="rounded-full bg-[var(--glass-strong)] px-2 py-1 text-xs font-semibold text-[var(--ink-muted)]">
          총 {total.toLocaleString()}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        <SourceOperationRow label="Slack" value={counts.slack ?? 0} total={total} tone="purple" />
        <SourceOperationRow label="Gmail" value={counts.gmail ?? 0} total={total} tone="blue" />
        <SourceOperationRow label="Google Drive" value={counts.drive ?? 0} total={total} tone="green" />
        <SourceOperationRow label="Google Calendar" value={counts.calendar ?? 0} total={total} tone="orange" />
        <SourceOperationRow label="기타" value={counts.other ?? 0} total={total} tone="gray" />
      </div>
    </div>
  );
}

function SourceOperationRow({ label, value, total, tone }: { label: string; value: number; total: number; tone: string }) {
  const percent = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="source-bar-row">
      <span>{label}</span>
      <div>
        <i className={tone} style={{ width: `${Math.max(percent, value > 0 ? 4 : 0)}%` }} />
      </div>
      <strong>{value.toLocaleString()}</strong>
      <em>({percent}%)</em>
    </div>
  );
}

/**
 * 파싱 품질(Body 파싱 성공 여부 등) 통계를 보여주는 컴포넌트
 */
function ParserQualityBreakdown({ counts }: { counts?: Record<string, number> }) {
  const rows = parserQualityRows(counts);
  if (rows.length === 0) {
    return null;
  }

  const total = rows.reduce((sum, row) => sum + row.count, 0);

  return (
    <div
      className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3 text-xs"
      data-testid="sync-parser-quality"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold text-[var(--ink-strong)]">Parser quality</p>
        <span className="text-[var(--ink-muted)]">{total.toLocaleString()} sources</span>
      </div>
      <div className="mt-2 grid gap-2">
        {rows.map((row) => (
          <div key={row.status} className="flex items-center justify-between gap-3 rounded-md bg-[var(--glass-strong)] px-2 py-1.5">
            <span className="font-medium">{row.label}</span>
            <span className={`rounded-full px-2 py-0.5 font-semibold ${row.className}`}>
              {row.count.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-2 leading-5 text-[var(--ink-muted)]">
        Metadata-only and unsupported files remain reviewable, but they are not treated as full body-parsed evidence.
      </p>
    </div>
  );
}

function SlackRuntimeStatusPanel({
  status,
  llmPreflight,
  llmAgentRunning,
  selectedChannelIds,
  onRunLlmAgent,
  onToggleChannel,
}: {
  status: SlackRuntimeStatus;
  llmPreflight?: AgentLlmPreflight;
  llmAgentRunning: boolean;
  selectedChannelIds: string[];
  onRunLlmAgent: () => void;
  onToggleChannel: (channelId: string) => void;
}) {
  const channelOptions =
    status.channel_options.length > 0
      ? status.channel_options
      : status.configured_channel_ids.map((channelId) => ({
          id: channelId,
          name: channelId,
          is_selected: true,
          is_configured: true,
        }));
  const channelLabel = selectedChannelIds.length > 0 ? selectedChannelIds.join(", ") : "선택 채널 없음";
  const latestSync = status.latest_sync;
  const syncSummary = status.latest_sync_summary;

  return (
    <div
      data-testid="slack-runtime-status"
      className="integration-glass-card rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3 text-sm"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--ink-strong)]">Slack 운영 상태</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            상태 조회는 sync나 LLM 호출을 실행하지 않습니다.
          </p>
        </div>
        <span className="liquid-control inline-flex rounded-full px-2 py-1 text-xs font-semibold text-[var(--ink-strong)]">
          <span>{status.mode}</span>
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs">
        <div className="glass-row flex items-center justify-between gap-3 rounded-md px-2 py-2">
          <span className="text-[var(--ink-muted)]">Sync 대상</span>
          <span className="max-w-[210px] truncate font-semibold">{channelLabel}</span>
        </div>
        <div className="glass-row flex items-center justify-between gap-3 rounded-md px-2 py-2">
          <span className="text-[var(--ink-muted)]">연결</span>
          <span className="font-semibold">{status.connection_status}</span>
        </div>
        <div className="glass-row flex items-center justify-between gap-3 rounded-md px-2 py-2">
          <span className="text-[var(--ink-muted)]">자격 증명</span>
          <span className="font-semibold">{status.credential_status}</span>
        </div>
      </div>

      {channelOptions.length > 0 ? (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span className="font-semibold text-[var(--ink-strong)]">채널 선택</span>
            <span className="text-[var(--ink-muted)]">{selectedChannelIds.length.toLocaleString()}개 선택</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {channelOptions.map((channel) => {
              const selected = selectedChannelIds.includes(channel.id);
              return (
                <button
                  key={channel.id}
                  type="button"
                  onClick={() => onToggleChannel(channel.id)}
                  className={`liquid-control inline-flex h-8 items-center gap-2 rounded-[18px] px-3 text-xs font-semibold ${
                    selected ? "text-[var(--ink-strong)]" : "text-[var(--ink-muted)] opacity-80"
                  }`}
                  aria-pressed={selected}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      selected ? "bg-[var(--workspace-rail-active)]" : "bg-[var(--line-strong)]"
                    }`}
                    aria-hidden="true"
                  />
                  {channel.name}
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="mt-3 rounded-md border border-dashed border-[var(--line-soft)] px-3 py-2 text-xs text-[var(--ink-muted)]">
          Slack 채널 ID를 설정하면 여기서 sync 대상을 선택할 수 있습니다.
        </p>
      )}

      <div className="glass-row mt-3 rounded-md px-2 py-2 text-xs">
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold">Agent 연결</span>
          <span className="font-semibold">
            {status.agent_bridge.ready_for_agent_test ? "테스트 가능" : "sync 필요"}
          </span>
        </div>
        <p className="mt-1 text-[var(--ink-muted)]">
          Slack source {status.agent_bridge.slack_source_count.toLocaleString()}개 · 대기 review{" "}
          {status.agent_bridge.pending_review_count.toLocaleString()}개
        </p>
      </div>

      {llmPreflight ? (
        <div className="glass-row mt-3 rounded-md px-2 py-2 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="font-semibold">실제 LLM 테스트</span>
            <span className="font-semibold">{llmPreflight.budget_status}</span>
          </div>
          <p className="mt-1 text-[var(--ink-muted)]">
            {llmPreflight.model_name ?? "모델 미설정"} · {llmPreflight.available_providers.join(" → ") || "API key 필요"}
          </p>
          <p className="mt-1 text-[var(--ink-muted)]">
            예상 {llmPreflight.estimated_total_tokens.toLocaleString()} tokens · $
            {llmPreflight.estimated_cost_usd.toFixed(6)}
            {llmPreflight.budget_limit_usd ? ` / $${llmPreflight.budget_limit_usd}` : ""}
          </p>
          <p className="mt-1 text-[var(--ink-muted)]">
            중요 evidence {llmPreflight.evidence_message_count.toLocaleString()} /{" "}
            {llmPreflight.max_evidence_messages.toLocaleString()}개 사용
            {llmPreflight.source_window ? ` · ${llmPreflight.source_window}` : ""}
          </p>
          <button
            type="button"
            onClick={() => onRunLlmAgent()}
            disabled={llmAgentRunning || llmPreflight.action !== "run"}
            className="liquid-primary mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-[20px] px-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-55"
          >
            <Bot className="h-4 w-4" aria-hidden="true" />
            {llmAgentRunning ? "실제 LLM 실행 중" : "실제 LLM 테스트 실행"}
          </button>
          {llmPreflight.action !== "run" ? (
            <p className="mt-2 text-[var(--ink-muted)]">상태: {llmPreflight.reason}</p>
          ) : null}
        </div>
      ) : null}

      {status.last_error ? (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
          <div className="flex items-center justify-between gap-3 font-semibold">
            <span>Slack 오류</span>
            <span>{status.last_error.code}</span>
          </div>
          <p className="mt-1">{status.last_error.action_hint}</p>
        </div>
      ) : null}

      {latestSync ? (
        <div className="glass-row mt-3 rounded-md px-2 py-2 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="font-semibold">최근 sync</span>
            <span className="font-semibold">{latestSync.status}</span>
          </div>
          <p className="mt-1 truncate text-[var(--ink-muted)]">{latestSync.message}</p>
          {syncSummary ? (
            <p className="mt-1 text-[var(--ink-muted)]">
              수집 {syncSummary.fetched_events.toLocaleString()} · 후보{" "}
              {syncSummary.created_review_items.toLocaleString()} · 중복{" "}
              {syncSummary.skipped_events.toLocaleString()}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function AgentLlmPreflightPanel({
  title,
  preflight,
  agentRunning,
  onRunAgent,
}: {
  title: string;
  preflight?: AgentLlmPreflight;
  agentRunning: boolean;
  onRunAgent: () => void;
}) {
  if (!preflight) {
    return null;
  }

  return (
    <div className="integration-glass-card rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--ink-strong)]">{title}</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            명시 확인 후에만 유료 LLM을 실행합니다. Mail/Docs는 GPT-5.4 mini로 업무 후보를 생성합니다.
          </p>
        </div>
        <span className="liquid-control inline-flex rounded-full px-2 py-1 text-xs font-semibold text-[var(--ink-strong)]">
          <span>{preflight.budget_status}</span>
        </span>
      </div>
      <div className="glass-row mt-3 rounded-md px-2 py-2 text-xs">
        <p className="font-semibold">
          {preflight.model_name ?? "모델 미설정"} · {preflight.available_providers.join(" → ") || "API key 필요"}
        </p>
        <p className="mt-1 text-[var(--ink-muted)]">
          예상 {preflight.estimated_total_tokens.toLocaleString()} tokens · $
          {preflight.estimated_cost_usd.toFixed(6)}
          {preflight.budget_limit_usd ? ` / $${preflight.budget_limit_usd}` : ""}
        </p>
        <p className="mt-1 text-[var(--ink-muted)]">
          evidence {preflight.evidence_message_count.toLocaleString()} /{" "}
          {preflight.max_evidence_messages.toLocaleString()}개
          {preflight.source_window ? ` · ${preflight.source_window}` : ""}
        </p>
        <button
          type="button"
          onClick={() => onRunAgent()}
          disabled={agentRunning || preflight.action !== "run"}
          className="liquid-primary mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-[20px] px-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-55"
        >
          <Bot className="h-4 w-4" aria-hidden="true" />
          {agentRunning ? "LLM 실행 중" : title.includes("Mail/Docs") ? "GPT-5.4 mini로 업무 후보 생성" : "유료 LLM 실행"}
        </button>
        {preflight.action !== "run" ? (
          <p className="mt-2 text-[var(--ink-muted)]">상태: {preflight.reason}</p>
        ) : null}
      </div>
    </div>
  );
}

function GoogleRuntimeStatusList({ statuses }: { statuses: Record<string, GoogleRuntimeStatus> }) {
  const rows = GOOGLE_CONNECTOR_TYPES.map((connectorType) => statuses[connectorType]).filter(Boolean);
  if (rows.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="google-runtime-status"
      className="integration-glass-card rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3 text-sm"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--ink-strong)]">Google 운영 상태</p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">Gmail, Drive, Calendar 상태를 한 번에 확인합니다.</p>
        </div>
        <span className="liquid-control inline-flex rounded-full px-2 py-1 text-xs font-semibold text-[var(--ink-strong)]">
          <span>{rows[0]?.mode ?? "mock"}</span>
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.map((status) => (
          <div key={status.connector_type} className="glass-row rounded-md px-2 py-2 text-xs">
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

function parserQualityRows(counts?: Record<string, number>) {
  const statusLabels: Record<string, string> = {
    parsed: "Parsed",
    metadata_only: "Metadata only",
    unsupported: "Unsupported",
  };
  const statusClasses: Record<string, string> = {
    parsed: "bg-emerald-50 text-emerald-800",
    metadata_only: "bg-amber-50 text-amber-800",
    unsupported: "bg-red-50 text-red-800",
  };

  return Object.entries(counts ?? {})
    .filter(([, count]) => count > 0)
    .sort(([left], [right]) => {
      const order = ["parsed", "metadata_only", "unsupported"];
      const leftIndex = order.indexOf(left);
      const rightIndex = order.indexOf(right);
      return (leftIndex === -1 ? order.length : leftIndex) - (rightIndex === -1 ? order.length : rightIndex);
    })
    .map(([status, count]) => ({
      status,
      count,
      label: statusLabels[status] ?? status,
      className: statusClasses[status] ?? "bg-[var(--glass-strong)] text-[var(--ink-strong)]",
    }));
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

function connectorDisplayName(type: string, manifests: IntegrationManifest[]) {
  return manifests.find((manifest) => manifest.type === type)?.display_name ?? formatConnectorName(type);
}

function formatConnectorName(connectorType: string) {
  if (connectorType === "slack") {
    return "Slack";
  }
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
