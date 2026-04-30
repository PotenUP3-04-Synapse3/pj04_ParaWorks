"use client";

import { CheckCircle2, FileSearch, Pencil, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { SourceEvidenceDrawer } from "@/components/shared/SourceEvidenceDrawer";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type { ReviewItem, ReviewItemUpdate, ReviewResponse } from "@/lib/api/types";

function stringField(value: unknown) {
  return typeof value === "string" ? value : "";
}

function itemTitle(item: ReviewItem) {
  const title = stringField(item.payload.title);
  return title || `Review item ${item.id}`;
}

function summaryKey(item: ReviewItem) {
  if (typeof item.payload.decision_summary === "string") {
    return "decision_summary";
  }
  if (typeof item.payload.reason === "string") {
    return "reason";
  }
  if (typeof item.payload.priority_reason === "string") {
    return "priority_reason";
  }
  return "summary";
}

function itemSummary(item: ReviewItem) {
  const summary = stringField(item.payload[summaryKey(item)]);
  return summary || "No summary was returned.";
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [editingId, setEditingId] = useState<number>();
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [pendingAction, setPendingAction] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(undefined);

    try {
      const review = await apiGet<ReviewResponse>("/api/v1/review?status=pending_review");
      setItems(review.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load review items");
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

  async function runStatusAction(item: ReviewItem, action: "approve" | "reject" | "request-more-evidence") {
    const actionKey = `${item.id}:${action}`;
    setPendingAction(actionKey);
    setError(undefined);

    try {
      const updated = await apiPost<ReviewItem>(`/api/v1/review/${item.id}/${action}`);
      setItems((current) => current.filter((candidate) => candidate.id !== updated.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review action failed");
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
      setItems((current) =>
        current.map((candidate) => (candidate.id === updated.id ? updated : candidate)),
      );
      setEditingId(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review update failed");
    } finally {
      setPendingAction(undefined);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted">Pending approval</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">Review Queue</h2>
        </div>
        <button
          type="button"
          onClick={() => void loadItems()}
          disabled={loading}
          className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <section className="space-y-3">
        {items.map((item) => {
          const isEditing = editingId === item.id;
          const editPending = pendingAction === `${item.id}:edit`;
          return (
            <article key={item.id} className="rounded-md border border-line bg-white p-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                      {item.item_type.replaceAll("_", " ")}
                    </span>
                    <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                      {item.permission_level}
                    </span>
                  </div>

                  {isEditing ? (
                    <div className="mt-3 max-w-3xl space-y-3">
                      <label className="block text-sm font-medium">
                        Title
                        <input
                          value={editTitle}
                          onChange={(event) => setEditTitle(event.target.value)}
                          className="mt-1 h-10 w-full rounded-md border border-line px-3 text-sm font-normal outline-none focus:border-neutral-500"
                        />
                      </label>
                      <label className="block text-sm font-medium">
                        Summary
                        <textarea
                          value={editSummary}
                          onChange={(event) => setEditSummary(event.target.value)}
                          rows={3}
                          className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm font-normal leading-6 outline-none focus:border-neutral-500"
                        />
                      </label>
                    </div>
                  ) : (
                    <>
                      <h3 className="mt-3 text-base font-semibold">{itemTitle(item)}</h3>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
                        {itemSummary(item)}
                      </p>
                    </>
                  )}
                </div>

                <div className="flex shrink-0 flex-col gap-3 sm:flex-row lg:items-start">
                  <div className="w-28">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted">Confidence</p>
                    <p className="mt-1 text-lg font-semibold">
                      {Math.round(item.confidence_score * 100)}%
                    </p>
                  </div>
                  <SourceEvidenceDrawer links={item.source_links} snippets={item.source_snippets} />
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void saveEdit(item)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-neutral-900 bg-neutral-900 px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      {editPending ? "Saving" : "Save edit"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(undefined)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => void runStatusAction(item, "approve")}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-neutral-900 bg-neutral-900 px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => void runStatusAction(item, "reject")}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Reject
                    </button>
                    <button
                      type="button"
                      onClick={() => startEdit(item)}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => void runStatusAction(item, "request-more-evidence")}
                      disabled={Boolean(pendingAction)}
                      className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
                    >
                      <FileSearch className="h-4 w-4" aria-hidden="true" />
                      Request more evidence
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}

        {!loading && items.length === 0 ? (
          <div className="rounded-md border border-line bg-white p-8 text-sm text-muted">
            No pending review items were returned.
          </div>
        ) : null}
        {loading ? (
          <div className="rounded-md border border-line bg-white p-8 text-sm text-muted">
            Loading review items.
          </div>
        ) : null}
      </section>
    </div>
  );
}
