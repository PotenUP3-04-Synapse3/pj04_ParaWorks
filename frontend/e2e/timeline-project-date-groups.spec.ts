import { expect, test } from "@playwright/test";

test("Timeline groups approved project items by date", async ({ page }) => {
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
            evidence_count: 0,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 0,
            evidence: [],
            activity_items: [],
            timeline_items: [
              {
                id: "timeline_event:1",
                item_type: "timeline_event",
                title: "오전 점검",
                summary: "Redis 점검",
                source_links: ["https://slack.example/1"],
                source_snippets: ["점검"],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T01:00:00Z",
                evidence_reason: "승인된 항목",
                project_key: "project-alpha",
              },
              {
                id: "timeline_event:2",
                item_type: "timeline_event",
                title: "오후 배포",
                summary: "배포 완료",
                source_links: ["https://slack.example/2"],
                source_snippets: ["배포"],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T06:00:00Z",
                evidence_reason: "승인된 항목",
                project_key: "project-alpha",
              },
              {
                id: "timeline_event:3",
                item_type: "timeline_event",
                title: "전날 회의",
                summary: "회의 완료",
                source_links: ["https://slack.example/3"],
                source_snippets: ["회의"],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-14T06:00:00Z",
                evidence_reason: "승인된 항목",
                project_key: "project-alpha",
              },
            ],
          },
        ],
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/timeline");

  await expect(page.getByText("2026년 5월 15일")).toBeVisible();
  await expect(page.getByText("2026년 5월 14일")).toBeVisible();
  await expect(page.getByText("오전 점검")).toBeVisible();
  await expect(page.getByText("오후 배포")).toBeVisible();
  await expect(page.getByText("전날 회의")).toBeVisible();

  await page.getByRole("button", { name: "Open 오전 점검" }).click();
  const sourceLink = page.getByRole("link", { name: "Open source" });
  await expect(sourceLink).toHaveAttribute("href", "https://slack.example/1");
  await expect(sourceLink).toHaveAttribute("target", "_blank");
  await expect(sourceLink).toHaveAttribute("rel", /noopener/);
});
