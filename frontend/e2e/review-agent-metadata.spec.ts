import { expect, test } from "@playwright/test";

const projectAssignmentItem = {
  id: 101,
  item_type: "project_assignment",
  payload: {
    title: "ParaWorks MVP source 연결",
    summary: "Slack 원본 근거를 ParaWorks MVP 프로젝트에 연결하는 검토 항목입니다.",
    agent_name: "project_classifier",
    project_key: "paraworks-mvp",
    project_name: "ParaWorks MVP",
    source_type: "slack",
    source_title: "마이그레이션 검증 논의",
    task_summary: "마이그레이션 검증 체계와 Review Queue 작업을 ParaWorks MVP로 묶습니다.",
    evidence_reason: '"ParaWorks MVP" 단서가 Slack 원문과 프로젝트 설명에서 발견되었습니다.',
  },
  source_links: ["https://example.com/slack/thread"],
  source_snippets: ["마이그레이션 검증 체계와 Review Queue 작업을 ParaWorks MVP로 묶습니다."],
  source_evidence: [],
  agent_run_id: null,
  agent_run_details: {
    model_name: "Unknown",
    prompt_version: "Unknown",
    estimated_cost_usd: 0,
    total_tokens: 0,
  },
  confidence_score: 0.82,
  permission_level: "internal",
  status: "pending_review",
  reviewer_id: null,
};

test("Review page labels deterministic project classifier metadata without unknown", async ({ page }) => {
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
    await route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } });
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
        projects: [{ project_key: "paraworks-mvp", name: "ParaWorks MVP" }],
      },
    });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        groups: [
          {
            group_id: "project_assignment:ParaWorks MVP source 연결",
            title: "ParaWorks MVP source 연결",
            item_type: "project_assignment",
            status: "pending_review",
            permission_level: "internal",
            items: [projectAssignmentItem],
            total_count: 1,
            avg_confidence: 0.82,
          },
        ],
        items: [projectAssignmentItem],
        total_count: 1,
        limit: 50,
        offset: 0,
        has_more: false,
        include_previews: false,
      },
    });
  });
  await page.route("**/api/v1/review/101/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "project_assignment",
        can_approve: true,
        missing_required_fields: [],
        normalized_payload: {
          title: "ParaWorks MVP source 연결",
          project_key: "paraworks-mvp",
        },
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/review");
  await expect(page.locator(".group-container")).toHaveCount(1);

  await expect(page.getByText("프로젝트 연결", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("project assignment");

  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("프로젝트 분류기")).toBeVisible();
  await expect(page.getByText("규칙 기반 프로젝트 연결")).toBeVisible();
  await expect(page.getByText("추가 LLM 비용 없음")).toBeVisible();
  await expect(page.getByText("프로젝트 연결 후보")).toBeVisible();
  await expect(page.getByText("추천 프로젝트: ParaWorks MVP")).toBeVisible();
  await expect(page.getByText("연결 내용: 마이그레이션 검증 체계와 Review Queue 작업을 ParaWorks MVP로 묶습니다.")).toBeVisible();
  await expect(page.getByText('분류 근거: "ParaWorks MVP" 단서가 Slack 원문과 프로젝트 설명에서 발견되었습니다.')).toBeVisible();
  await expect(page.getByText("원본: 마이그레이션 검증 논의")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("LLM 미사용");
  await expect(page.locator("body")).not.toContainText(/\bunknown\b/i);
});
