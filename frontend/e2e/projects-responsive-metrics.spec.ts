import { expect, test } from "@playwright/test";

test("Project metrics do not overlap on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
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
            name: "아주 긴 프로젝트 이름으로 레이아웃 확인",
            summary: "모바일 겹침 확인",
            source_types: ["slack"],
            evidence_count: 1234,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 987,
            evidence: [],
            activity_items: [
              {
                id: "todo:1",
                item_type: "todo",
                title: "활동",
                summary: "활동",
                source_links: [],
                source_snippets: [],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T02:00:00Z",
                evidence_reason: "근거",
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

  const metrics = page.locator('[data-testid="project-metric"]');
  await expect(metrics).toHaveCount(3);
  for (let index = 0; index < 3; index += 1) {
    await expect(metrics.nth(index)).toBeVisible();
  }
});
