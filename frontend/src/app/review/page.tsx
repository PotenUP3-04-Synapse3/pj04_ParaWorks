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
  ChevronDown,
  ChevronRight,
  Layers,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { SourceEvidenceDrawer } from "@/components/shared/SourceEvidenceDrawer";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type {
  ReviewItem,
  ReviewEvidenceRequest,
  ReviewItemUpdate,
  ReviewPromotionPreview,
} from "@/lib/api/types";

// 타입 확장
type ReviewGroup = {
  group_id: string;
  title: string;
  item_type: string;
  status: string;
  permission_level: string;
  items: ReviewItem[];
  total_count: number;
  avg_confidence: number;
};

type ReviewResponse = {
  groups: ReviewGroup[];
  items: ReviewItem[];
};

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

function itemTitle(item: ReviewItem | ReviewGroup) {
  if ('payload' in item) {
    const title = stringField(item.payload.title);
    return title || `Review item ${item.id}`;
  }
  return item.title;
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

function formatCost(value: unknown) {
  const cost = numberField(value);
  if (cost === undefined) return undefined;
  return `$${cost.toFixed(6)}`;
}

export default function ReviewPage() {
  const [groups, setGroups] = useState<ReviewGroup[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
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
      setGroups(review.groups || []);
      
      // 모든 항목에 대한 프리뷰 로드
      const allItems = (review.groups || []).flatMap(g => g.items || []);
      const previewPairs = await Promise.all(
        allItems.map(async (item) => [
          item.id,
          await apiGet<ReviewPromotionPreview>(`/api/v1/review/${item.id}/promotion-preview`),
        ] as const),
      );
      setPreviews(Object.fromEntries(previewPairs));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검토 항목을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadItems();
  }, [loadItems]);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }));
  };

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
      
      // 로컬 상태 업데이트: 해당 항목 제거
      setGroups((current) => 
        current.map(group => ({
          ...group,
          items: group.items.filter(i => i.id !== updated.id)
        })).filter(group => group.items.length > 0)
      );

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
      
      setGroups((current) =>
        current.map(group => ({
          ...group,
          items: group.items.map(i => i.id === updated.id ? updated : i)
        }))
      );
      setPreviews((current) => ({ ...current, [updated.id]: preview }));
      setEditingId(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "검토 항목 수정에 실패했습니다.");
    } finally {
      setPendingAction(undefined);
    }
  }

  const totalAgentItems = groups.reduce((acc, g) => acc + g.items.filter(i => Boolean(i.payload.agent_name)).length, 0);

  return (
    <div className="reference-dashboard space-y-5">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Review Items</p>
          <h1>검토사항</h1>
          <p>
            유사한 항목들은 그룹화되어 표시됩니다. 각 그룹을 펼쳐 상세 내용을 확인하세요.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-[var(--ink-muted)] shadow-sm">
            <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            Agent 후보 {totalAgentItems}개
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

      <section className="space-y-4">
        {groups.map((group) => {
          const isExpanded = expandedGroups[group.group_id];
          const hasMultiple = group.total_count > 1;

          return (
            <div key={group.group_id} className="group-container overflow-hidden rounded-xl border border-[var(--line-soft)] bg-[var(--glass-elevated)] shadow-sm">
              {/* Group Header */}
              <div 
                onClick={() => toggleGroup(group.group_id)}
                className="flex cursor-pointer items-center justify-between border-b border-[var(--line-soft)] bg-[var(--glass-strong)] px-4 py-3 hover:bg-[var(--glass-stronger)]"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                  <span className="rounded-full border border-[var(--line-soft)] bg-white/50 px-2.5 py-0.5 text-xs font-bold text-[var(--ink-muted)]">
                    {itemTypeLabel(group.item_type)}
                  </span>
                  <h3 className="text-base font-bold">{group.title}</h3>
                  {hasMultiple && (
                    <span className="flex items-center gap-1 rounded-md bg-[var(--workspace-rail-active)] px-2 py-0.5 text-xs font-bold text-white">
                      <Layers className="h-3 w-3" />
                      {group.total_count}개 중복/유사
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                   <div className="text-right">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--ink-muted)]">평균 신뢰도</p>
                      <p className="text-sm font-bold">{Math.round(group.avg_confidence * 100)}%</p>
                   </div>
                </div>
              </div>

              {/* Group Items */}
              {isExpanded && (
                <div className="divide-y divide-[var(--line-soft)] bg-white/30">
                  {group.items.map((item) => {
                    const isEditing = editingId === item.id;
                    const editPending = pendingAction === `${item.id}:edit`;
                    const agentName = stringField(item.payload.agent_name);
                    const promptVersion = stringField(item.payload.prompt_version);
                    const cost = formatCost(item.payload.estimated_cost_usd);
                    const isAgentItem = Boolean(agentName);
                    const preview = previews[item.id];
                    const canApprove = preview?.can_approve ?? true;
                    const evidenceRows = item.source_evidence ?? [];
                    const isEvidenceRequestOpen = evidenceRequestId === item.id;
                    const evidenceRequestPending = pendingAction === `${item.id}:request-more-evidence`;

                    return (
                      <div key={item.id} className="p-5">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
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
                                <h4 className="mt-3 text-sm font-bold text-[var(--ink-muted)]">#{item.id} 상세 내용</h4>
                                <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink)]">
                                  {itemSummary(item)}
                                </p>
                              </>
                            )}

                            {isAgentItem ? (
                              <div className="mt-4 flex flex-wrap gap-3">
                                <MetadataTile label="Prompt" value={promptVersion || "unknown"} />
                                <MetadataTile label="Cost" value={cost ?? "unknown"} />
                              </div>
                            ) : null}

                            {preview ? (
                              <div className="mt-4 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--ink-muted)]">
                                    승인 시 저장 데이터 구조
                                  </p>
                                  <span
                                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                      preview.can_approve
                                        ? "bg-emerald-100 text-emerald-800"
                                        : "bg-red-100 text-red-800"
                                    }`}
                                  >
                                    {preview.can_approve ? "승격 가능" : "필수 정보 부족"}
                                  </span>
                                </div>
                                <dl className="mt-2 grid gap-x-4 gap-y-2 sm:grid-cols-2">
                                  {Object.entries(preview.normalized_payload).map(([key, value]) => (
                                    <div key={key} className="min-w-0">
                                      <dt className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">{key}</dt>
                                      <dd className="mt-0.5 truncate text-xs font-medium">{value || "-"}</dd>
                                    </div>
                                  ))}
                                </dl>
                              </div>
                            ) : null}
                          </div>

                          <div className="flex shrink-0 flex-col gap-3 sm:flex-row xl:items-start">
                            <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] px-3 py-2 text-center min-w-[80px]">
                              <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--ink-muted)]">신뢰도</p>
                              <p className="mt-1 text-lg font-bold">{Math.round(item.confidence_score * 100)}%</p>
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

                        <div className="mt-4 flex flex-wrap gap-2 border-t border-dashed border-[var(--line-soft)] pt-4">
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
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {!loading && groups.length === 0 ? (
          <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-8 text-sm text-[var(--ink-muted)] shadow-sm text-center">
            대기 중인 검토 항목이 없습니다.
          </div>
        ) : null}
        {loading && groups.length === 0 ? (
          <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] p-8 text-sm text-[var(--ink-muted)] shadow-sm text-center">
            검토 항목을 불러오는 중입니다...
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
