import { expect, test } from "@playwright/test";

test("Dashboard shows today's approved todos and hides completed task only on the page", async ({ page }) => {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });

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
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        source_counts: {},
        pending_review_count: 0,
        recent_jobs: [],
        pending_items: [],
        today_todos: [
          {
            id: 101,
            title: "오늘 고객사 공유본 보내기",
            assignee: "김하나",
            due_date: today,
            category: "Project Alpha",
            priority: "high",
          },
        ],
        assigned_projects: [
          {
            project_key: "project-alpha",
            name: "Project Alpha",
            summary: "승인 활동이 있는 프로젝트입니다.",
            evidence_count: 2,
            activity_count: 3,
            pending_review_count: 1,
            latest_timestamp: `${today}T09:00:00+09:00`,
            permission_level: "internal",
          },
        ],
        recent_decisions: [],
        recent_timeline: [],
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/dashboard");

  await expect(page.getByText("오늘 고객사 공유본 보내기")).toBeVisible();
  await expect(page.getByText("Project Alpha").first()).toBeVisible();
  await expect(page.getByText("근거 2건 · 활동 3건 · 검토 대기 1건")).toBeVisible();

  await page.getByRole("button", { name: "완료 오늘 고객사 공유본 보내기" }).click();

  await expect(page.getByText("오늘 고객사 공유본 보내기")).toBeHidden();
  await expect(page.getByText("오늘 처리할 승인된 할 일이 없습니다.")).toBeVisible();
});
