"use client";

import {
  Bot,
  CheckCircle2,
  Coins,
  FileSearch,
  Pencil,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { SourceEvidenceDrawer } from "@/components/shared/SourceEvidenceDrawer";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type {
  ReviewItem,
  ReviewEvidenceRequest,
  ReviewItemUpdate,
  ReviewPromotionPreview,
  ReviewResponse,
} from "@/lib/api/types";

function stringField(value: unknown) {
  return typeof value === "string" ? value : "";
}

function numberField(value: unknown) {
  return typeof value === "number" ? value : undefined;
}

function recordField(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function itemTitle(item: ReviewItem) {
  const title = stringField(item.payload.title);
  return title || `Review item ${item.id}`;
}

function summaryKey(item: ReviewItem) {
  if (typeof item.payload.summary === "string") return "summary";
  if (typeof item.payload.decision_summary === "string") return "decision_summary";
  if (typeof item.payload.reason === "string") return "reason";
  if (typeof item.payload.priority_reason === "string") return "priority_reason";
  return "summary";
}

function itemSummary(item: ReviewItem) {
  const summary = stringField(item.payload[summaryKey(item)]);
  return summary || "요약을 생성하지 못했습니다. 근거를 확인한 뒤 수정하거나 추가 근거를 요청하세요.";
}

function itemTypeLabel(itemType: string) {
  const labels: Record<string, string> = {
    decision_record: "결정 기록",
    history_event: "히스토리",
    timeline_event: "타임라인",
    todo: "할 일",
    message_review: "메시지 검토",
  };
  return labels[itemType] ?? itemType.replaceAll("_", " ");
}

const FALLBACK_REVIEW_ITEMS: ReviewItem[] = [
  {
    id: 9001,
    item_type: "history_event",
    payload: {
      title: "ORION 요구사항 변경 검토",
      summary: "고객사가 관리자 리포트 권한 분리와 감사 로그 보존 기간 확대를 요청했습니다. 일정 영향과 권한 정책 변경 여부를 검토해야 합니다.",
      agent_name: "Slack Agent",
      prompt_version: "demo.v1",
      token_usage: { total_tokens: 1840 },
      estimated_cost_usd: 0.0024,
      cache_key: "demo-orion-requirement-change",
    },
    source_links: ["paraworks://slack/project-orion/1746940920.000100"],
    source_snippets: ["고객사가 관리자 리포트 권한을 더 세분화해 달라고 요청했습니다."],
    source_evidence: [],
    agent_run_id: null,
    confidence_score: 0.88,
    permission_level: "internal",
    status: "pending_review",
  },
  {
    id: 9002,
    item_type: "decision_record",
    payload: {
      title: "Oracle DB 선정 근거 확인",
      summary: "운영 안정성, 기존 라이선스, 장애 대응 경험을 이유로 Oracle DB 유지 의견이 우세합니다.",
      agent_name: "Mail/Docs Agent",
      prompt_version: "demo.v1",
      token_usage: { total_tokens: 1260 },
      estimated_cost_usd: 0.0018,
      cache_key: "demo-orion-db-selection",
    },
    source_links: ["paraworks://gmail/thread/orion-db-selection"],
    source_snippets: ["운영팀 장애 대응 경험까지 같이 적으면 근거가 더 명확합니다."],
    source_evidence: [],
    agent_run_id: null,
    confidence_score: 0.82,
    permission_level: "internal",
    status: "pending_review",
  },
  {
    id: 9003,
    item_type: "todo",
    payload: {
      title: "보안 정책 초안 코멘트",
      summary: "관리자 권한 변경 알림과 개인정보 접근 로그 보존 기준을 정책 초안에 반영해야 합니다.",
    },
    source_links: ["paraworks://drive/nova-security-policy"],
    source_snippets: ["관리자 권한 변경은 알림과 감사 로그가 모두 필요합니다."],
    source_evidence: [],
    agent_run_id: null,
    confidence_score: 0.76,
    permission_level: "restricted",
    status: "pending_review",
  },
];

function formatCost(value: unknown) {
  const cost = numberField(value);
  if (cost === undefined) return undefined;
  return `$${cost.toFixed(6)}`;
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>(FALLBACK_REVIEW_ITEMS);
  const [editingId, setEditingId] = useState<number>();
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [evidenceRequestId, setEvidenceRequestId] = useState<number>();
  const [evidenceRequestNote, setEvidenceRequestNote] = useState("");
  const [previews, setPreviews] = useState<Record<number, ReviewPromotionPreview>>({});
  const [pendingAction, setPendingAction] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(undefined);

    try {
      const review = await apiGet<ReviewResponse>("/api/v1/review?status=pending_review");
      setItems(review.items);
      const previewPairs = await Promise.all(
        review.items.map(async (item) => [
          item.id,
          await apiGet<ReviewPromotionPreview>(`/api/v1/review/${item.id}/promotion-preview`),
        ] as const),
      );
      setPreviews(Object.fromEntries(previewPairs));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검토 항목을 불러오지 못했습니다.");
      setItems(FALLBACK_REVIEW_ITEMS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadItems();
  }, [loadItems]);

  function startEdit(item: ReviewItem) {
    setEditingId(item.id);
    setEditTitle(itemTitle(item));
    setEditSummary(itemSummary(item));
    setError(undefined);
  }

  async function runStatusAction(
    item: ReviewItem,
    action: "approve" | "reject" | "request-more-evidence",
    body?: ReviewEvidenceRequest,
  ) {
    const actionKey = `${item.id}:${action}`;
    setPendingAction(actionKey);
    setError(undefined);

    try {
      const updated = await apiPost<ReviewItem>(`/api/v1/review/${item.id}/${action}`, body);
      setItems((current) => current.filter((candidate) => candidate.id !== updated.id));
      if (action === "request-more-evidence") {
        setEvidenceRequestId(undefined);
        setEvidenceRequestNote("");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검토 작업에 실패했습니다.");
    } finally {
      setPendingAction(undefined);
    }
  }

  async function saveEdit(item: ReviewItem) {
    const key = summaryKey(item);
    const update: ReviewItemUpdate = {
      payload: {
        ...item.payload,
        title: editTitle,
        [key]: editSummary,
      },
    };

    setPendingAction(`${item.id}:edit`);
    setError(undefined);

    try {
      const updated = await apiPatch<ReviewItem>(`/api/v1/review/${item.id}`, update);
      const preview = await apiGet<ReviewPromotionPreview>(`/api/v1/review/${item.id}/promotion-preview`);
      setItems((current) =>
        current.map((candidate) => (candidate.id === updated.id ? updated : candidate)),
      );
      setPreviews((current) => ({ ...current, [updated.id]: preview }));
      setEditingId(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검토 항목 수정에 실패했습니다.");
    } finally {
      setPendingAction(undefined);
    }
  }

  const agentItems = items.filter((item) => Boolean(item.payload.agent_name)).length;

  return (
    <div className="reference-dashboard space-y-5">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Review Items</p>
          <h1>검토사항</h1>
          <p>
            AI Agent와 connector가 만든 후보를 사람이 확인하고 승인해야 공식 지식으로 승격됩니다.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-[var(--ink-muted)] shadow-sm">
            <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            Agent 후보 {agentItems}개
          </span>
          <button
            type="button"
            onClick={() => void loadItems()}
            disabled={loading}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink shadow-sm hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            새로고침
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <section className="space-y-3">
        {items.map((item) => {
          const isEditing = editingId === item.id;
          const editPending = pendingAction === `${item.id}:edit`;
          const agentName = stringField(item.payload.agent_name);
          const promptVersion = stringField(item.payload.prompt_version);
          const cacheKey = stringField(item.payload.cache_key);
          const cost = formatCost(item.payload.estimated_cost_usd);
          const tokenUsage = recordField(item.payload.token_usage);
          const totalTokens = numberField(tokenUsage?.total_tokens);
          const isAgentItem = Boolean(agentName);
          const preview = previews[item.id];
          const canApprove = preview?.can_approve ?? true;
          const evidenceRows = item.source_evidence ?? [];
          const isEvidenceRequestOpen = evidenceRequestId === item.id;
          const evidenceRequestPending = pendingAction === `${item.id}:request-more-evidence`;

          return (
            <article key={item.id} className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-4 shadow-sm">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold text-[var(--ink-muted)]">
                      {itemTypeLabel(item.item_type)}
                    </span>
                    <span className="rounded-full border border-[var(--line-soft)] bg-[var(--glass-strong)] px-2.5 py-1 text-xs font-semibold capitalize text-[var(--ink-muted)]">
                      {item.permission_level}
                    </span>
                    {isAgentItem ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#21132b] px-2.5 py-1 text-xs font-semibold text-white">
                        <Sparkles className="h-3 w-3" aria-hidden="true" />
                        {agentName}
                      </span>
                    ) : (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                        Human/Connector
                      </span>
                    )}
                  </div>

                  {isEditing ? (
                    <div className="mt-3 max-w-3xl space-y-3">
                      <label className="block text-sm font-semibold">
                        제목
                        <input
                          value={editTitle}
                          onChange={(event) => setEditTitle(event.target.value)}
                          className="mt-1 h-10 w-full rounded-lg border border-[var(--line-soft)] px-3 text-sm font-normal outline-none focus:border-[#21132b]"
                        />
                      </label>
                      <label className="block text-sm font-semibold">
                        요약
                        <textarea
                          value={editSummary}
                          onChange={(event) => setEditSummary(event.target.value)}
                          rows={3}
                          className="mt-1 w-full rounded-lg border border-[var(--line-soft)] px-3 py-2 text-sm font-normal leading-6 outline-none focus:border-[#21132b]"
                        />
                      </label>
                    </div>
                  ) : (
                    <>
                      <h3 className="mt-3 text-base font-semibold">{itemTitle(item)}</h3>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
                        {itemSummary(item)}
                      </p>
                    </>
                  )}

                  {isAgentItem ? (
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <MetadataTile label="Prompt" value={promptVersion || "unknown"} />
                      <MetadataTile label="Tokens" value={totalTokens?.toLocaleString("ko-KR") ?? "unknown"} />
                      <MetadataTile label="Cost" value={cost ?? "unknown"} />
                      <MetadataTile label="Cache" value={cacheKey ? `${cacheKey.slice(0, 10)}...` : "none"} />
                    </div>
                  ) : null}

                  {preview ? (
                    <div className="mt-4 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                          승인 후 저장 형태 · {itemTypeLabel(preview.target_type)}
                        </p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                            preview.can_approve
                              ? "bg-[#ecfbf6] text-[#0f6f58]"
                              : "bg-red-50 text-red-700"
                          }`}
                        >
                          {preview.can_approve ? "승인 가능" : "필수 필드 필요"}
                        </span>
                      </div>
                      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                        {Object.entries(preview.normalized_payload).map(([key, value]) => (
                          <div key={key} className="min-w-0">
                            <dt className="text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                              {key}
                            </dt>
                            <dd className="mt-0.5 truncate text-sm font-medium">{value || "비어 있음"}</dd>
                          </div>
                        ))}
                      </dl>
                      {preview.missing_required_fields.length > 0 ? (
                        <p className="mt-3 text-xs font-medium text-red-700">
                          누락 필드: {preview.missing_required_fields.join(", ")}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                <div className="flex shrink-0 flex-col gap-3 sm:flex-row xl:items-start">
                  <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] px-3 py-2">
                    <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                      <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                      신뢰도
                    </p>
                    <p className="mt-1 text-lg font-semibold">
                      {Math.round(item.confidence_score * 100)}%
                    </p>
                  </div>
                  <SourceEvidenceDrawer
                    evidence={evidenceRows}
                    links={item.source_links}
                    snippets={item.source_snippets}
                    itemTitle={itemTitle(item)}
                    agentRunId={item.agent_run_id}
                  />
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--line-soft)] pt-4">
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void saveEdit(item)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      {editPending ? "저장 중" : "수정 저장"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(undefined)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      취소
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => void runStatusAction(item, "approve")}
                      disabled={Boolean(pendingAction) || !canApprove}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      승인
                    </button>
                    <button
                      type="button"
                      onClick={() => void runStatusAction(item, "reject")}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      반려
                    </button>
                    <button
                      type="button"
                      onClick={() => startEdit(item)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                      수정
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEvidenceRequestId(item.id);
                        setEvidenceRequestNote(
                          "현재 근거만으로는 승인하기 어렵습니다. 원문 링크, 담당자 발언, 결정 시점을 추가로 확인해주세요.",
                        );
                      }}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
                    >
                      <FileSearch className="h-4 w-4" aria-hidden="true" />
                      근거 추가 요청
                    </button>
                  </>
                )}
              </div>
              {isEvidenceRequestOpen ? (
                <div className="mt-3 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-3">
                  <label className="block text-sm font-semibold text-[var(--ink)]">
                    추가로 필요한 근거
                    <textarea
                      value={evidenceRequestNote}
                      onChange={(event) => setEvidenceRequestNote(event.target.value)}
                      rows={3}
                      className="mt-2 w-full rounded-lg border border-[var(--line-soft)] bg-[var(--surface)] px-3 py-2 text-sm font-normal leading-6 text-[var(--ink)] outline-none focus:border-[var(--workspace-rail-active)]"
                    />
                  </label>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        void runStatusAction(item, "request-more-evidence", {
                          note: evidenceRequestNote,
                        })
                      }
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
                    >
                      <FileSearch className="h-4 w-4" aria-hidden="true" />
                      {evidenceRequestPending ? "요청 중" : "요청 보내기"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEvidenceRequestId(undefined);
                        setEvidenceRequestNote("");
                      }}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      취소
                    </button>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}

        {!loading && items.length === 0 ? (
          <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-8 text-sm text-[var(--ink-muted)] shadow-sm">
            대기 중인 검토 항목이 없습니다.
          </div>
        ) : null}
        {loading && items.length === 0 ? (
          <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-8 text-sm text-[var(--ink-muted)] shadow-sm">
            검토 항목을 불러오는 중입니다.
          </div>
        ) : null}
      </section>
    </div>
  );
}

function MetadataTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] px-3 py-2">
      <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
        <Coins className="h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}
