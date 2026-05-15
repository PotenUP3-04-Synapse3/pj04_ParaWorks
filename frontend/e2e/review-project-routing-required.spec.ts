import { expect, test } from "@playwright/test";

const item = {
  id: 501,
  item_type: "history_event",
  payload: {
    title: "새 캠페인 킥오프",
    summary: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
    agent_name: "slack_agent",
    project_assignment_method: "llm_tool",
    project_assignment_summary: "등록된 프로젝트와 직접 일치하지 않습니다.",
    project_assignment_reason: "프로젝트 설명과 일치하는 근거가 부족해 사용자 선택이 필요합니다.",
    project_assignment_confidence: 0.41,
    project_needs_user_selection: true,
  },
  source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
  source_snippets: ["새 캠페인 준비 논의"],
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

test("Slack LLM routed item requires project selection before approval", async ({ page }) => {
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
    await route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { pending_review_count: 1, source_counts: { slack: 1, gmail: 0, drive: 0, calendar: 0, other: 0 } },
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
            group_id: "history_event:새 캠페인 킥오프",
            title: "새 캠페인 킥오프",
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            items: [item],
            total_count: 1,
            avg_confidence: 0.82,
          },
        ],
        items: [item],
        total_count: 1,
        limit: 50,
        offset: 0,
        has_more: false,
        include_previews: false,
      },
    });
  });
  await page.route("**/api/v1/review/501/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: false,
        missing_required_fields: ["project_key"],
        normalized_payload: {
          title: "새 캠페인 킥오프",
          reason: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
          project_key: "",
        },
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/review");
  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("프로젝트 선택 후 승인 가능")).toBeVisible();
  await expect(page.getByText("새 프로젝트 만들기")).toBeVisible();
  await expect(page.getByRole("button", { name: "승인", exact: true })).toBeDisabled();
  await expect(page.getByLabel("프로젝트 지정")).toHaveValue("");
});
