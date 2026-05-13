export const REVIEW_QUEUE_UPDATED_EVENT = "paraworks:review-queue-updated";

export function notifyReviewQueueUpdated() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(REVIEW_QUEUE_UPDATED_EVENT));
}
