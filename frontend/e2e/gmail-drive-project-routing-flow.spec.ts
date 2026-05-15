import { expect, test } from "@playwright/test";

const baseUser = {
  id: "demo-admin",
  email: "admin@paraworks.com",
  role: "admin",
  permission_levels: ["public", "internal", "restricted"],
  name: "ParaWorks Admin",
  title: "Workspace Administrator",
  department: "Platform",
};

test("Gmail and Drive routed review requires project selection before approval and appears in Timeline and Projects", async ({
  page,
}) => {
  let selectedProjectKey = "";
  let approved = false;

  const reviewItem = () => ({
    id: 701,
    item_type: "history_event",
    payload: {
      title: "Gmail 계약 후속 일정 확정",
      summary: "고객 계약서 회신과 Drive 제안서 검토 일정이 확정되었습니다.",
      agent_name: "mail_document_agent",
      project_assignment_method: "llm_tool",
      project_assignment_summary: selectedProjectKey
        ? "Gmail 본문과 Drive 제안서가 Project Alpha 업무와 연결됩니다."
        : "등록된 프로젝트와 자동 매칭되지 않아 검토자 선택이 필요합니다.",
      project_assignment_reason: selectedProjectKey
        ? "메일 제목, 고객명, Drive 파일명이 Project Alpha 설명과 일치합니다."
        : "Gmail/Drive 증거만으로는 등록 프로젝트를 확정할 수 없습니다.",
      project_assignment_confidence: selectedProjectKey ? 0.88 : 0.39,
      project_needs_user_selection: !selectedProjectKey,
      source_ids: ["gmail:message-1", "drive:file-1"],
      source_types: ["gmail", "drive"],
      ...(selectedProjectKey
        ? { project_key: "project-alpha", project_name: "Project Alpha" }
        : {}),
    },
    source_links: ["https://mail.google.com/mail/u/0/#inbox/message-1", "https://drive.google.com/file/d/file-1/view"],
    source_snippets: ["고객 계약서 회신은 금요일까지 필요합니다.", "Project Alpha 제안서 검토 일정"],
    source_evidence: [],
    agent_run_id: 77,
    agent_run_details: {
      model_name: "gpt-5.4-mini",
      prompt_version: "mail-docs:v2",
      estimated_cost_usd: 0.00008,
      total_tokens: 320,
    },
    confidence_score: 0.82,
    permission_level: "internal",
    status: "pending_review",
    reviewer_id: null,
  });

  const projectsPayload = () => ({
    project_count: 1,
    hidden_project_count: 0,
    hidden_evidence_count: 0,
    projects: [
      {
        project_key: "project-alpha",
        name: "Project Alpha",
        summary: "Gmail/Drive 승인 항목이 연결된 프로젝트입니다.",
        source_types: ["gmail", "drive"],
        evidence_count: 0,
        permission_level: "internal",
        latest_timestamp: "2026-05-15T06:00:00Z",
        pending_review_count: approved ? 0 : selectedProjectKey ? 1 : 0,
        evidence: [],
        timeline_items: approved
          ? [
              {
                id: "timeline_event:701",
                item_type: "timeline_event",
                title: "Gmail 계약 후속 일정 확정",
                summary: "고객 계약서 회신과 Drive 제안서 검토 일정이 확정되었습니다.",
                source_links: ["https://mail.google.com/mail/u/0/#inbox/message-1"],
                source_snippets: ["고객 계약서 회신은 금요일까지 필요합니다."],
                confidence_score: 0.82,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T06:00:00Z",
                evidence_reason: "승인된 Gmail/Drive 항목",
                project_key: "project-alpha",
              },
            ]
          : [],
        activity_items: approved
          ? [
              {
                id: "history_event:701",
                item_type: "history_event",
                title: "Gmail 계약 후속 일정 확정",
                summary: "고객 계약서 회신과 Drive 제안서 검토 일정이 확정되었습니다.",
                source_links: ["https://mail.google.com/mail/u/0/#inbox/message-1"],
                source_snippets: ["고객 계약서 회신은 금요일까지 필요합니다."],
                confidence_score: 0.82,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T06:00:00Z",
                evidence_reason: "승인된 Gmail/Drive 항목",
                project_key: "project-alpha",
              },
            ]
          : [],
      },
    ],
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { user: baseUser } });
  });
  await page.route("**/api/v1/notifications", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { pending_review_count: approved ? 0 : 1, source_counts: { gmail: 1, drive: 1 } },
    });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { projects: [{ project_key: "project-alpha", name: "Project Alpha", summary: "Gmail Drive work" }] },
    });
  });
  await page.route("**/api/v1/projects", async (route) => {
    await route.fulfill({ contentType: "application/json", json: projectsPayload() });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: approved
        ? { groups: [], items: [], total_count: 0, limit: 50, offset: 0, has_more: false, include_previews: false }
        : {
            groups: [
              {
                group_id: "history_event:Gmail 계약 후속 일정 확정",
                title: "Gmail 계약 후속 일정 확정",
                item_type: "history_event",
                status: "pending_review",
                permission_level: "internal",
                items: [reviewItem()],
                total_count: 1,
                avg_confidence: 0.82,
              },
            ],
            items: [reviewItem()],
            total_count: 1,
            limit: 50,
            offset: 0,
            has_more: false,
            include_previews: false,
          },
    });
  });
  await page.route("**/api/v1/review/701/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: Boolean(selectedProjectKey),
        missing_required_fields: selectedProjectKey ? [] : ["project_key"],
        normalized_payload: {
          title: "Gmail 계약 후속 일정 확정",
          reason: "고객 계약서 회신과 Drive 제안서 검토 일정이 확정되었습니다.",
          project_key: selectedProjectKey,
        },
      },
    });
  });
  await page.route("**/api/v1/review/701", async (route) => {
    const request = route.request();
    if (request.method() !== "PATCH") return route.fallback();
    const body = request.postDataJSON() as { payload?: { project_key?: string } };
    selectedProjectKey = body.payload?.project_key ?? "";
    await route.fulfill({ contentType: "application/json", json: reviewItem() });
  });
  await page.route("**/api/v1/review/701/approve", async (route) => {
    approved = true;
    await route.fulfill({
      contentType: "application/json",
      json: {
        ...reviewItem(),
        status: "approved",
        promotion_result: {
          target_type: "history_event",
          created_record_ids: [701],
          created_timeline_event_ids: [701],
          project_key: "project-alpha",
          next_routes: ["/timeline", "/projects"],
        },
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/review");
  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("프로젝트 선택 후 승인할 수 있습니다.")).toBeVisible();
  await expect(page.getByRole("button", { name: "승인", exact: true })).toBeDisabled();

  await page.getByLabel("프로젝트 지정").selectOption("project-alpha");
  await expect(page.getByRole("button", { name: "승인", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "승인", exact: true }).click();

  await page.goto("/timeline");
  await expect(page.getByText("Gmail 계약 후속 일정 확정")).toBeVisible();
  await expect(page.getByText("2026년 5월 15일")).toBeVisible();

  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Project Alpha" })).toBeVisible();
  await expect(page.getByText("Gmail 계약 후속 일정 확정")).toBeVisible();
});
