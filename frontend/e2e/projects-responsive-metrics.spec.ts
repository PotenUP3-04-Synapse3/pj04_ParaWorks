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

test("Projects page presents a responsive workspace layout", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 900 });
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
            project_key: "project-k",
            name: "케크",
            summary: "변시 사업부 승인된 원본 근거 71건과 승인된 프로젝트 활동 75건이 연결되어 있습니다.",
            source_types: ["drive"],
            evidence_count: 71,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 0,
            evidence: [
              {
                id: "project-k:drive-1",
                source_id: "drive-1",
                source_type: "drive",
                title: "케크 파일럿용 보안 정책 v2.0 문서 변경",
                source_url: "https://drive.example/security",
                source_snippet: "외부 파트너 MFA 의무화",
                permission_level: "internal",
                timestamp: "2026-05-15T02:00:00Z",
                task_summary: "케크 파일럿 전용 보안 정책 문서에 외부 파트너 MFA 의무화가 포함되어 있습니다.",
                evidence_reason: "승인된 히스토리 기록이 이 프로젝트와 연결되어 있습니다.",
              },
            ],
            activity_items: [
              {
                id: "todo:1",
                item_type: "todo",
                title: "케크 보안 정책 후속 할 일",
                summary: "담당자와 기한을 확정합니다.",
                source_links: ["https://drive.example/security"],
                source_snippets: ["외부 파트너 MFA 의무화"],
                confidence_score: 0.9,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T02:00:00Z",
                evidence_reason: "승인된 할 일입니다.",
                project_key: "project-k",
              },
            ],
            timeline_items: [],
          },
          {
            project_key: "paraworks",
            name: "ParaWorks",
            summary: "시스템 설명 원무 승인된 원본 근거 217건과 승인된 프로젝트 활동 150건이 연결되어 있습니다.",
            source_types: ["slack"],
            evidence_count: 217,
            permission_level: "internal",
            latest_timestamp: "2026-05-15T02:00:00Z",
            pending_review_count: 3,
            evidence: [],
            activity_items: [],
            timeline_items: [],
          },
        ],
      },
    });
  });
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/projects");

  await expect(page.getByTestId("project-workspace")).toBeVisible();
  await expect(page.getByTestId("project-overview-hero")).toContainText("케크");
  await expect(page.getByTestId("project-list-panel")).toContainText("2개 프로젝트");
  await expect(page.getByTestId("project-evidence-panel")).toContainText("연결된 원본 근거");
  await expect(page.getByTestId("project-evidence-tabs")).toContainText("Drive");
  await expect(page.getByTestId("project-activity-panel")).toContainText("승인된 프로젝트 활동");
  await expect(page.getByTestId("project-activity-timeline")).toBeVisible();

  const gridColumns = await page.getByTestId("project-workspace-grid").evaluate((element) => {
    return window.getComputedStyle(element).gridTemplateColumns.split(" ").length;
  });
  expect(gridColumns).toBeLessThanOrEqual(2);
});
