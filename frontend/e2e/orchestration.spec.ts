import { expect, test } from "@playwright/test";

test("agent runs page can execute a zero-cost LangGraph dry-run", async ({ page }) => {
  await page.route("**/api/v1/orchestration/company-memory/dry-run**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        workflow_name: "company_memory",
        backend: "langgraph",
        objective: "answer_from_company_memory",
        inputs: { question: "Redis queue state" },
        completed_nodes: [
          "collect_evidence",
          "draft_review_candidates",
          "retrieve_company_memory",
          "answer_with_rag",
        ],
        outputs: {
          review_boundary: "human_approval_required",
          token_budget_policy: "delta_sync_hash_skip_evidence_budget",
        },
        token_cost_usd: 0,
        cost_policy: {
          delta_sync: true,
          source_hash_skip: true,
          evidence_token_budget: true,
          paid_llm_calls_in_status_api: false,
        },
      },
    });
  });

  await page.goto("/agent-runs");
  await expect(page.getByTestId("app-shell")).toHaveAttribute("data-hydrated", "true");
  await page.getByRole("button", { name: "Dry-run 실행" }).click();

  await expect(page.getByText("Dry-run 완료")).toBeVisible();
  await expect(page.getByText("4개 노드 실행")).toBeVisible();
  await expect(page.getByText("토큰 비용 $0")).toBeVisible();
  await expect(page.getByText("delta_sync_hash_skip_evidence_budget")).toBeVisible();
});
