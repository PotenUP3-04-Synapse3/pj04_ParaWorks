import { expect, test } from "@playwright/test";

const today = "2026-05-15";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
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
    await route.fulfill({ contentType: "application/json", json: { counts: { total: 4 }, notifications: [] } });
  });
});

test("dashboard renders polished SaaS layout with interactive calendar", async ({ page }) => {
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        source_counts: {},
        pending_review_count: 30,
        recent_jobs: [],
        pending_items: [
          { id: 1, title: "프로젝트 리스크 리뷰 일정 확인", item_type: "timeline_event", category: "검토", confidence_score: 0.92 },
          { id: 2, title: "신규 기능 요구사항 워크숍 일정", item_type: "timeline_event", category: "검토", confidence_score: 0.91 },
          { id: 3, title: "개발 릴리즈 체크리스트 일정", item_type: "timeline_event", category: "검토", confidence_score: 0.9 },
        ],
        today_todos: [],
        today_events: [
          {
            id: 201,
            title: "Teacher's Day",
            start: `${today}T09:00:00+09:00`,
            end: `${today}T09:30:00+09:00`,
            location: "",
            organizer: "en.south_korea#holiday@group.v.calendar.google.com",
            attendee_summary: "",
            source_url: "https://calendar.google.com/event?eid=holiday",
            permission_level: "public",
          },
          {
            id: 202,
            title: "금요일 주간 마감 정리",
            start: `${today}T16:30:00+09:00`,
            end: `${today}T17:00:00+09:00`,
            location: "",
            organizer: "hanvv3@gmail.com",
            attendee_summary: "",
            source_url: "https://calendar.google.com/event?eid=weekly",
            permission_level: "internal",
          },
        ],
        assigned_projects: [],
        recent_decisions: [],
        recent_timeline: [],
      },
    });
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
            group_id: "timeline_event:프로젝트 리스크 리뷰 일정 확인",
            title: "프로젝트 리스크 리뷰 일정 확인",
            item_type: "timeline_event",
            status: "pending_review",
            permission_level: "internal",
            items: [
              {
                id: 1,
                item_type: "timeline_event",
                payload: { title: "프로젝트 리스크 리뷰 일정 확인", summary: "검토 큐의 실제 항목입니다." },
                source_links: [],
                source_snippets: [],
                source_evidence: [],
                agent_run_id: null,
                agent_run_details: { model_name: null, prompt_version: null, estimated_cost_usd: null, total_tokens: 0 },
                confidence_score: 0.92,
                permission_level: "internal",
                status: "pending_review",
                reviewer_id: null,
              },
            ],
            total_count: 1,
            avg_confidence: 0.92,
          },
        ],
        items: [],
        total_count: 1,
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
      json: { target_type: "timeline_event", can_approve: true, missing_required_fields: [], normalized_payload: {} },
    });
  });

  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "오늘의 업무 흐름" })).toBeVisible();
  await expect(page.getByText("오늘도 좋은 흐름으로 시작해볼까요?")).toBeVisible();
  await expect(page.getByText("오늘 할 일", { exact: true })).toBeVisible();
  await expect(page.getByText("내 검토 대기", { exact: true })).toBeVisible();
  await expect(page.getByText("30건", { exact: true })).toBeVisible();
  await expect(page.getByLabel("오늘의 핵심 지표").getByText("오늘 일정", { exact: true })).toBeVisible();
  await expect(page.getByText("2개", { exact: true })).toBeVisible();
  await expect(page.getByLabel("오늘의 핵심 지표").getByText("담당 프로젝트", { exact: true })).toBeVisible();
  await expect(page.getByText("오늘 처리할 승인된 할 일이 없습니다.")).toBeVisible();
  await expect(page.locator("#dashboard-tasks").getByRole("link", { name: /타임라인 보기/ })).toHaveAttribute("href", "/timeline");
  await expect(
    page.locator("section.dashboard-card").filter({ hasText: "담당 프로젝트" }).getByRole("link", { name: /프로젝트 보기/ }),
  ).toHaveAttribute("href", "/projects");
  await expect(page.getByText("프로젝트 리스크 리뷰 일정 확인")).toBeVisible();
  await expect(page.getByText("신규 기능 요구사항 워크숍 일정")).toBeVisible();
  await expect(page.getByText("개발 릴리즈 체크리스트 일정")).toBeVisible();
  await expect(page.getByTestId("dashboard-review-count")).toHaveText("30");
  await expect(page.getByTestId("dashboard-review-card").locator(".dashboard-review-row")).toHaveCount(3);
  await expect(page.getByTestId("dashboard-review-link-1")).toHaveAttribute("href", "/review?itemId=1");
  await page.getByTestId("dashboard-review-link-1").click();
  await expect(page).toHaveURL(/\/review\?itemId=1$/);
  await expect(page.getByTestId("review-item-1")).toBeVisible();
  await expect(page.getByTestId("review-item-1")).toContainText("검토 큐의 실제 항목입니다.");
  await page.goBack();
  await expect(page.getByTestId("dashboard-calendar")).toBeVisible();
  await expect(page.getByTestId("dashboard-calendar")).toHaveCSS("position", "static");
  const heroBox = await page.locator(".dashboard-hero").boundingBox();
  const heroCopyBox = await page.locator(".dashboard-hero-copy").boundingBox();
  const heroIllustrationBox = await page.locator(".dashboard-hero-illustration").boundingBox();
  const calendarBox = await page.getByTestId("dashboard-calendar").boundingBox();
  expect(heroBox?.height).toBeLessThanOrEqual(250);
  expect(heroIllustrationBox?.width).toBeGreaterThan(260);
  expect(heroCopyBox && heroIllustrationBox ? heroCopyBox.x + heroCopyBox.width < heroIllustrationBox.x : false).toBeTruthy();
  expect(calendarBox?.height).toBeLessThanOrEqual(620);
  await expect(page.getByTestId("dashboard-calendar").getByRole("heading", { name: "2026년 5월" })).toBeVisible();
  await expect(page.locator(".dashboard-calendar-weekdays span")).toHaveText(["일", "월", "화", "수", "목", "금", "토"]);
  const selectedDateStyle = await page.getByTestId("calendar-day-2026-05-15").evaluate((element) => {
    const style = window.getComputedStyle(element);
    return { backgroundColor: style.backgroundColor, backgroundImage: style.backgroundImage };
  });
  const todayDateStyle = await page.getByTestId("calendar-day-2026-05-16").evaluate((element) => {
    const style = window.getComputedStyle(element);
    return { backgroundColor: style.backgroundColor, backgroundImage: style.backgroundImage };
  });
  expect(selectedDateStyle.backgroundImage).toContain("linear-gradient");
  expect(todayDateStyle.backgroundImage).toBe("none");
  expect(todayDateStyle.backgroundColor).not.toBe("rgba(0, 0, 0, 0)");
  await expect(page.getByText("09:00")).toBeVisible();
  await expect(page.getByText("Teacher's Day")).toBeVisible();
  await expect(page.getByText("16:30")).toBeVisible();
  await expect(page.getByText("금요일 주간 마감 정리")).toBeVisible();
  await expect(page.getByText("내게 온 업데이트")).toHaveCount(0);

  const sidebarOverflow = await page.locator(".app-sidebar").evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(sidebarOverflow.scrollWidth).toBeLessThanOrEqual(sidebarOverflow.clientWidth);
  expect(sidebarOverflow.scrollHeight).toBeLessThanOrEqual(sidebarOverflow.clientHeight);

  await page.getByTestId("calendar-day-2026-05-16").hover();
  await expect(page.getByText("일정 없음")).toBeVisible();
});

test("dashboard completes approved todo through the API and hides it", async ({ page }) => {
  let completedTodoId: number | undefined;

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
            completed_at: null,
          },
        ],
        today_events: [
          {
            id: 201,
            title: "Customer renewal meeting",
            start: `${today}T10:30:00+09:00`,
            end: `${today}T11:00:00+09:00`,
            location: "Zoom",
            organizer: "organizer@example.com",
            attendee_summary: "2 accepted, 1 tentative",
            source_url: "https://calendar.google.com/event?eid=today",
            permission_level: "internal",
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
  await page.route("**/api/v1/todos/101/complete", async (route) => {
    completedTodoId = 101;
    await route.fulfill({
      contentType: "application/json",
      json: {
        id: 101,
        title: "오늘 고객사 공유본 보내기",
        status: "completed",
        completed_at: `${today}T09:30:00+09:00`,
        completed_by: "demo-admin",
      },
    });
  });

  await page.goto("/dashboard");

  await expect(page.getByText("오늘 고객사 공유본 보내기")).toBeVisible();
  await expect(page.getByText("Customer renewal meeting")).toBeVisible();
  await expect(page.getByText("10:30")).toBeVisible();
  await expect(page.getByText("2 accepted, 1 tentative")).toBeVisible();
  await expect(page.getByText("Project Alpha").first()).toBeVisible();
  await expect(page.getByText("근거 2건 · 활동 3건 · 검토 대기 1건")).toBeVisible();

  await page.getByRole("button", { name: "완료 오늘 고객사 공유본 보내기" }).click();

  expect(completedTodoId).toBe(101);
  await expect(page.getByText("오늘 고객사 공유본 보내기")).toBeHidden();
  await expect(page.getByText("오늘 처리할 승인된 할 일이 없습니다.")).toBeVisible();
});

test("dashboard calendar keeps today selected when synced events start in a previous month", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-05-17T09:00:00+09:00"));

  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        source_counts: {},
        pending_review_count: 0,
        recent_jobs: [],
        pending_items: [],
        today_todos: [],
        today_events: [],
        calendar_events: [
          {
            id: 401,
            title: "지난달 연동 일정",
            start: "2026-04-17T10:00:00+09:00",
            end: "2026-04-17T11:00:00+09:00",
            location: "",
            organizer: "calendar@example.com",
            attendee_summary: "",
            source_url: "https://calendar.google.com/event?eid=april",
            permission_level: "internal",
          },
        ],
        assigned_projects: [],
        recent_decisions: [],
        recent_timeline: [],
      },
    });
  });

  await page.goto("/dashboard");

  await expect(page.getByTestId("dashboard-calendar").getByRole("heading", { name: "2026년 5월" })).toBeVisible();
  await expect(page.getByText("5월 17일 일")).toBeVisible();
  await expect(page.getByTestId("calendar-day-2026-05-17")).toHaveClass(/selected/);
});
