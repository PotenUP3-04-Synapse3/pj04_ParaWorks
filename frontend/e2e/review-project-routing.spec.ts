import { expect, test } from "@playwright/test";

const routedReviewItem = {
  id: 201,
  item_type: "history_event",
  payload: {
    title: "Redis 큐 상태 확인",
    summary: "Redis 큐와 동기화 작업 상태를 확인했습니다.",
    agent_name: "slack_agent",
    project_key: "project-alpha",
    project_name: "Project Alpha",
    project_assignment_method: "llm_tool",
    project_assignment_summary: "Redis 큐 상태와 동기화 안정성 개선 논의입니다.",
    project_assignment_reason: "Redis와 sync job 근거가 Project Alpha와 일치합니다.",
    project_assignment_confidence: 0.86,
  },
  source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
  source_snippets: ["Redis queue 상태를 확인하고 sync job을 복구합니다."],
  source_evidence: [],
  agent_run_id: 10,
  agent_run_details: {
    model_name: "gpt-5-mini",
    prompt_version: "slack-taxonomy:v3",
    estimated_cost_usd: 0.00006,
    total_tokens: 210,
  },
  confidence_score: 0.91,
  permission_level: "internal",
  status: "pending_review",
  reviewer_id: null,
};

test("Review item shows LLM project routing summary and reason", async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal", "restricted"],
          name: "ParaWorks Admin",
          title: "Workspace Administrator",
          department: "Platform",
        },
      },
    });
  });
  await page.route("**/api/v1/notifications", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { unread_count: 0, notifications: [] },
    });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: 1,
        source_counts: { slack: 1, gmail: 0, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        projects: [
          {
            project_key: "project-alpha",
            name: "Project Alpha",
            summary: "Redis queue work",
          },
        ],
      },
    });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        groups: [
          {
            group_id: "history_event:Redis 큐 상태 확인",
            title: "Redis 큐 상태 확인",
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            items: [routedReviewItem],
            total_count: 1,
            avg_confidence: 0.91,
          },
        ],
        items: [routedReviewItem],
        total_count: 1,
        limit: 50,
        offset: 0,
        has_more: false,
        include_previews: false,
      },
    });
  });
  await page.route("**/api/v1/review/201/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: true,
        missing_required_fields: [],
        normalized_payload: {
          title: "Redis 큐 상태 확인",
          reason: "Redis 큐와 동기화 작업 상태를 확인했습니다.",
        },
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/review");
  await expect(page.locator(".group-container")).toHaveCount(1);

  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("LLM 프로젝트 분류")).toBeVisible();
  await expect(page.getByText("Redis 큐 상태와 동기화 안정성 개선 논의입니다.")).toBeVisible();
  await expect(page.getByText("Redis와 sync job 근거가 Project Alpha와 일치합니다.")).toBeVisible();
});
