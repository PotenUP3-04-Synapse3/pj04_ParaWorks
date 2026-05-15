import { expect, test } from "@playwright/test";

test("Projects page exposes original source links for evidence and approved activities", async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal"],
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
  await page.route("**/api/v1/projects", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        project_count: 1,
        hidden_project_count: 0,
        hidden_evidence_count: 0,
        projects: [
          {
            project_key: "project-alpha",
            name: "Project Alpha",
            summary: "Redis work",
            source_types: ["slack"],
            evidence_count: 1,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 0,
            evidence: [
              {
                id: "project-alpha:https://slack.example/activity/1",
                source_id: "https://slack.example/activity/1",
                source_type: "slack",
                title: "Redis 장애 대응 완료",
                source_url: "https://slack.example/activity/1",
                source_snippet: "장애 대응 완료",
                permission_level: "internal",
                timestamp: "2026-05-15T02:00:00Z",
                task_summary: "장애 대응이 완료되었습니다.",
                evidence_reason: "승인된 히스토리 기록입니다.",
              },
            ],
            activity_items: [
              {
                id: "history_event:1",
                item_type: "history_event",
                title: "Redis 장애 대응 완료",
                summary: "장애 대응이 완료되었습니다.",
                source_links: ["https://slack.example/activity/1"],
                source_snippets: ["장애 대응 완료"],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T02:00:00Z",
                occurred_at: "2026-05-15T02:00:00Z",
                evidence_reason: "승인된 히스토리 기록입니다.",
                project_key: "project-alpha",
              },
            ],
            timeline_items: [],
          },
        ],
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/projects");

  const evidenceLink = page.getByRole("link", { name: "원본 근거 열기 Redis 장애 대응 완료", exact: true }).first();
  await expect(evidenceLink).toHaveAttribute("href", "https://slack.example/activity/1");
  await expect(evidenceLink).toHaveAttribute("target", "_blank");
  await expect(evidenceLink).toHaveAttribute("rel", /noopener/);

  const activityLink = page.getByRole("link", { name: "원본 근거 열기 Redis 장애 대응 완료", exact: true }).nth(1);
  await expect(activityLink).toHaveAttribute("href", "https://slack.example/activity/1");
  await expect(activityLink).toHaveAttribute("target", "_blank");
  await expect(activityLink).toHaveAttribute("rel", /noopener/);
});

test("Projects page opens on the first project that already has approved evidence", async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal"],
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
  await page.route("**/api/v1/projects", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        project_count: 2,
        hidden_project_count: 0,
        hidden_evidence_count: 0,
        projects: [
          {
            project_key: "project-empty",
            name: "빈 프로젝트",
            summary: "아직 승인된 근거가 없습니다.",
            source_types: [],
            evidence_count: 0,
            permission_level: "internal",
            latest_timestamp: "",
            pending_review_count: 0,
            evidence: [],
            activity_items: [],
            timeline_items: [],
          },
          {
            project_key: "project-alpha",
            name: "Project Alpha",
            summary: "승인 근거가 있는 프로젝트입니다.",
            source_types: ["slack"],
            evidence_count: 1,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 0,
            evidence: [
              {
                id: "project-alpha:https://slack.example/activity/1",
                source_id: "https://slack.example/activity/1",
                source_type: "slack",
                title: "Redis 장애 대응 완료",
                source_url: "https://slack.example/activity/1",
                source_snippet: "장애 대응 완료",
                permission_level: "internal",
                timestamp: "2026-05-15T02:00:00Z",
                task_summary: "장애 대응이 완료되었습니다.",
                evidence_reason: "승인된 히스토리 기록입니다.",
              },
            ],
            activity_items: [],
            timeline_items: [],
          },
        ],
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/projects");

  await expect(page.getByRole("heading", { name: "Project Alpha" })).toBeVisible();
  await expect(page.getByText("Redis 장애 대응 완료")).toBeVisible();
  await expect(page.getByRole("heading", { name: "빈 프로젝트" })).toBeHidden();
});
