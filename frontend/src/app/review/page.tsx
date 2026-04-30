import { SourceEvidenceDrawer } from "@/components/shared/SourceEvidenceDrawer";
import { apiGet } from "@/lib/api/client";
import type { ReviewItem, ReviewResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

function itemTitle(item: ReviewItem) {
  const title = item.payload.title;
  return typeof title === "string" ? title : `Review item ${item.id}`;
}

function itemSummary(item: ReviewItem) {
  const summary =
    item.payload.decision_summary ?? item.payload.reason ?? item.payload.priority_reason;
  return typeof summary === "string" ? summary : "No summary was returned.";
}

export default async function ReviewPage() {
  const review = await apiGet<ReviewResponse>("/api/v1/review?status=pending_review");

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-muted">Pending approval</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">Review Queue</h2>
      </div>

      <section className="space-y-3">
        {review.items.map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                    {item.item_type.replaceAll("_", " ")}
                  </span>
                  <span className="rounded border border-line px-2 py-1 text-xs font-medium capitalize text-muted">
                    {item.permission_level}
                  </span>
                </div>
                <h3 className="mt-3 text-base font-semibold">{itemTitle(item)}</h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{itemSummary(item)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <div className="w-28">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted">Confidence</p>
                  <p className="mt-1 text-lg font-semibold">{Math.round(item.confidence_score * 100)}%</p>
                </div>
                <SourceEvidenceDrawer links={item.source_links} snippets={item.source_snippets} />
              </div>
            </div>
          </article>
        ))}
        {review.items.length === 0 ? (
          <div className="rounded-md border border-line bg-white p-8 text-sm text-muted">
            No pending review items were returned.
          </div>
        ) : null}
      </section>
    </div>
  );
}
