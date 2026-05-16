import { expect, test } from "@playwright/test";

const baseItem = {
  item_type: "history_event",
  payload: {
    summary: "Needs review.",
    agent_name: "slack_agent",
    project_assignment_method: "llm_tool",
    project_needs_user_selection: true,
  },
  source_links: ["https://slack.mock/archives/C123/p1"],
  source_snippets: ["Evidence snippet."],
  source_evidence: [],
  agent_run_id: 1,
  agent_run_details: {
    model_name: "gpt-5-mini",
    prompt_version: "slack-taxonomy:v3",
    estimated_cost_usd: 0.0001,
    total_tokens: 150,
  },
  confidence_score: 0.82,
  permission_level: "internal",
  status: "pending_review",
  reviewer_id: null,
};

const firstItem = {
  ...baseItem,
  id: 801,
  payload: { ...baseItem.payload, title: "First candidate" },
};

const secondItem = {
  ...baseItem,
  id: 802,
  payload: { ...baseItem.payload, title: "Second candidate" },
};

test("review queue supports Gmail-style selection, project routing, modal confirmation, and context actions", async ({ page }) => {
  const patchedProjects: Record<number, string> = {};
  let bulkPayload: unknown;

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal", "restricted"],
          name: "Admin",
          title: "Admin",
          department: "Platform",
        },
      },
    });
  });
  await page.route("**/api/v1/notifications", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { counts: { total: 0 }, notifications: [] } });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { pending_review_count: 2, source_counts: { slack: 2, gmail: 0, drive: 0, calendar: 0, other: 0 } },
    });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { projects: [{ project_key: "project-alpha", name: "Project Alpha" }] },
    });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        groups: [
          {
            group_id: "history_event:Duplicated candidate",
            title: "Duplicated candidate",
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            items: [firstItem, secondItem],
            total_count: 2,
            avg_confidence: 0.82,
          },
        ],
        items: [firstItem, secondItem],
        total_count: 2,
        limit: 50,
        offset: 0,
        has_more: false,
        include_previews: false,
      },
    });
  });
  await page.route("**/api/v1/review/*/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: true,
        missing_required_fields: [],
        normalized_payload: { title: "Candidate", project_key: "project-alpha" },
      },
    });
  });
  await page.route("**/api/v1/review/801", async (route) => {
    const body = await route.request().postDataJSON();
    patchedProjects[801] = body.payload.project_key;
    await route.fulfill({ contentType: "application/json", json: firstItem });
  });
  await page.route("**/api/v1/review/802", async (route) => {
    const body = await route.request().postDataJSON();
    patchedProjects[802] = body.payload.project_key;
    await route.fulfill({ contentType: "application/json", json: secondItem });
  });
  await page.route("**/api/v1/review/bulk", async (route) => {
    bulkPayload = await route.request().postDataJSON();
    await route.fulfill({
      contentType: "application/json",
      json: {
        action: "approve",
        approved_count: 2,
        rejected_count: 0,
        failed_items: [],
        skipped_items: [],
        approved_item_ids: [801, 802],
        rejected_item_ids: [],
      },
    });
  });
  await page.route("**/api/v1/review/801/reject", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { ...firstItem, status: "rejected" } });
  });

  await page.goto("/review");
  const groupHeader = page.locator(".group-container > div:first-child");
  await expect(groupHeader.locator(".lucide-chevron-right, .lucide-chevron-down")).toHaveCount(0);
  await page.getByTestId("review-group-select-history_event:Duplicated candidate").click();
  await expect(page.getByTestId("review-selected-count")).toContainText("2");
  await page.getByTestId("review-group-similar-approve-history_event:Duplicated candidate").click();
  await expect(page.getByTestId("review-bulk-confirm")).toContainText("2");
  await page.getByRole("button", { name: "취소" }).click();
  await page.getByTestId("review-group-select-history_event:Duplicated candidate").click();
  await expect(page.getByTestId("review-selected-count")).toContainText("0");
  await groupHeader.click();

  await page.getByTestId("review-select-all").click();
  await expect(page.getByTestId("review-selected-count")).toContainText("2");
  await page.getByTestId("review-bulk-project").selectOption("project-alpha");
  await page.getByTestId("review-bulk-approve").click();
  await expect(page.getByTestId("review-bulk-confirm")).toBeVisible();
  await expect(page.getByTestId("review-bulk-confirm")).toContainText("2");
  const backdropBox = await page.getByTestId("review-bulk-backdrop").boundingBox();
  const viewport = page.viewportSize();
  expect(backdropBox?.x).toBe(0);
  expect(backdropBox?.y).toBe(0);
  expect(backdropBox?.width).toBe(viewport?.width);
  expect(backdropBox?.height).toBe(viewport?.height);
  await page.getByTestId("confirm-bulk-action").click();

  expect(patchedProjects).toEqual({ 801: "project-alpha", 802: "project-alpha" });
  expect(bulkPayload).toEqual({ action: "approve", item_ids: [801, 802] });

  await page.getByTestId("review-item-801").click({ button: "right" });
  await expect(page.getByTestId("review-context-menu")).toBeVisible();
  await expect(page.getByTestId("review-context-reject")).toBeVisible();
});

test("review bulk failure message is readable Korean", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal", "restricted"],
          name: "Admin",
          title: "Admin",
          department: "Platform",
        },
      },
    });
  });
  await page.route("**/api/v1/notifications", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { counts: { total: 0 }, notifications: [] } });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { pending_review_count: 1, source_counts: {} } });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { projects: [] } });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        groups: [
          {
            group_id: "history_event:Needs project",
            title: "Needs project",
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            items: [firstItem],
            total_count: 1,
            avg_confidence: 0.82,
          },
        ],
        items: [firstItem],
        total_count: 1,
        limit: 50,
        offset: 0,
        has_more: false,
        include_previews: false,
      },
    });
  });
  await page.route("**/api/v1/review/bulk", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        action: "approve",
        approved_count: 0,
        rejected_count: 0,
        failed_items: [{ id: 801, detail: "project_key required" }],
        skipped_items: [],
        approved_item_ids: [],
        rejected_item_ids: [],
      },
    });
  });

  await page.goto("/review");
  await page.getByTestId("review-approve-loaded").click();
  await page.getByTestId("confirm-bulk-action").click();

  await expect(page.getByText("승인 처리 중 1개 항목은 건너뛰었습니다. 필수 정보와 근거를 확인해 주세요.")).toBeVisible();
});
