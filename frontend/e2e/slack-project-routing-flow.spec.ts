import { expect, test } from "@playwright/test";

const baseItem = {
  id: 602,
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

const preflight = {
  action: "run",
  reason: "ready",
  budget_status: "within_budget",
  model_name: "gpt-5-mini",
  provider_order: ["openai"],
  available_providers: ["openai"],
  estimated_input_tokens: 100,
  estimated_output_tokens: 50,
  estimated_total_tokens: 150,
  estimated_cost_usd: 0.001,
  budget_limit_usd: 1,
  evidence_message_count: 10,
  max_evidence_messages: 50,
  source_window: "slack:live:ranked",
  requires_paid_confirmation: true,
};

test("Slack project routing flows from sync to review approval and project timeline", async ({ page }) => {
  let syncQueued = false;
  let projectSelected = false;
  let approved = false;

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
      json: { pending_review_count: approved ? 0 : 1, source_counts: { slack: 210, gmail: 0, drive: 0, calendar: 0, other: 0 } },
    });
  });
  await page.route("**/api/v1/integrations", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          type: "slack",
          display_name: "Slack",
          mode: "live",
          status: "ready",
          auth_type: "oauth",
          required_scopes: ["channels:history"],
          sync_strategy: "incremental",
          cost_policy: "변경된 원본만 분석합니다.",
        },
      ],
    });
  });
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { connector_type: "slack", configured: false, install_url: null, state: null, required_scopes: [] },
    });
  });
  await page.route("**/api/v1/integrations/slack/runtime-status", async (route) => {
    const latestSync = syncQueued
      ? {
          job_id: "slack-routing-flow",
          status: "complete",
          message: "fetched=210 created_review_items=1 skipped_events=0 pending_review_items=1",
          progress_pct: 100,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
      : null;
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        mode: "live",
        configured_channel_ids: ["C123"],
        selected_channel_ids: ["C123"],
        channel_options: [{ id: "C123", name: "C123", is_selected: true, is_configured: true }],
        connection_status: "connected",
        credential_status: "available",
        latest_sync: latestSync,
        latest_sync_summary: syncQueued ? { fetched_events: 210, created_review_items: 1, skipped_events: 0 } : null,
        last_error: null,
        agent_bridge: {
          slack_source_count: 210,
          pending_review_count: approved ? 0 : 1,
          ready_for_agent_test: true,
        },
        cost_policy: {
          status_lookup_triggers_sync: false,
          status_lookup_triggers_llm: false,
          thread_reply_fetch_is_incremental: true,
        },
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/agent-review/llm/preflight", async (route) => {
    await route.fulfill({ contentType: "application/json", json: preflight });
  });
  await page.route("**/api/v1/integrations/mail-docs/agent-review/llm/preflight", async (route) => {
    await route.fulfill({ contentType: "application/json", json: preflight });
  });
  await page.route("**/api/v1/integrations/slack/sync", async (route) => {
    syncQueued = true;
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "slack-routing-flow",
        connector_type: "slack",
        status: "queued",
        created_review_items: 0,
        pending_review_count: 1,
        fetched_events: 0,
        skipped_events: 0,
        parser_status_counts: {},
        changed_source_ids: [],
        agent_generated_items: 0,
        project_assignment_items: 0,
      },
    });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { projects: [{ project_key: "project-alpha", name: "Project Alpha" }] },
    });
  });
  await page.route("**/api/v1/review?status=pending_review**", async (route) => {
    const item = {
      ...baseItem,
      payload: {
        ...baseItem.payload,
        ...(projectSelected
          ? {
              project_key: "project-alpha",
              project_name: "Project Alpha",
              project_needs_user_selection: false,
            }
          : {}),
      },
    };
    await route.fulfill({
      contentType: "application/json",
      json: approved
        ? { groups: [], items: [], total_count: 0, limit: 50, offset: 0, has_more: false, include_previews: false }
        : {
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
  await page.route("**/api/v1/review/602/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: projectSelected,
        missing_required_fields: projectSelected ? [] : ["project_key"],
        normalized_payload: {
          title: "새 캠페인 킥오프",
          reason: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
          project_key: projectSelected ? "project-alpha" : "",
        },
      },
    });
  });
  await page.route("**/api/v1/review/602", async (route) => {
    if (route.request().method() === "PATCH") {
      projectSelected = true;
      await route.fulfill({ contentType: "application/json", json: { ...baseItem, payload: { ...baseItem.payload, project_key: "project-alpha", project_name: "Project Alpha", project_needs_user_selection: false } } });
      return;
    }
    await route.fallback();
  });
  await page.route("**/api/v1/review/602/approve", async (route) => {
    approved = true;
    await route.fulfill({
      contentType: "application/json",
      json: {
        ...baseItem,
        status: "approved",
        payload: { ...baseItem.payload, project_key: "project-alpha", project_name: "Project Alpha", project_needs_user_selection: false },
        promotion_result: {
          target_type: "history_event",
          created_record_ids: [1],
          created_timeline_event_ids: [1],
          project_key: "project-alpha",
          next_routes: ["/timeline"],
        },
      },
    });
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
            activity_items: [
              {
                id: "history_event:1",
                item_type: "history_event",
                title: "새 캠페인 킥오프",
                summary: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
                source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
                source_snippets: ["새 캠페인 준비 논의"],
                confidence_score: 0.82,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T02:00:00Z",
                evidence_reason: "승인된 히스토리 기록이 이 프로젝트와 연결되어 있습니다.",
                project_key: "project-alpha",
              },
            ],
            timeline_items: [
              {
                id: "timeline_event:1",
                item_type: "timeline_event",
                title: "새 캠페인 킥오프",
                summary: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
                source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
                source_snippets: ["새 캠페인 준비 논의"],
                confidence_score: 0.82,
                permission_level: "internal",
                review_status: "approved",
                created_at: "2026-05-15T02:00:00Z",
                evidence_reason: "승인된 타임라인 항목이 이 프로젝트와 연결되어 있습니다.",
                project_key: "project-alpha",
              },
            ],
          },
        ],
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("slack-card-actions")).toBeVisible();
  await page.getByTestId("slack-card-actions").getByRole("button", { name: "동기화" }).click();
  await expect(page.getByTestId("sync-progress-modal")).toContainText("동기화 완료");
  await page.getByRole("button", { name: "닫기", exact: true }).click();

  await page.goto("/review");
  await page.locator(".group-container > div:first-child").click();
  await expect(page.getByText("프로젝트 선택 후 승인 가능")).toBeVisible();
  await page.getByLabel("프로젝트 지정").selectOption("project-alpha");
  await expect(page.getByRole("button", { name: "승인", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "승인", exact: true }).click();

  await page.goto("/timeline");
  await expect(page.getByRole("heading", { name: /5월 15일/ })).toBeVisible();
  await expect(page.getByText("새 캠페인 킥오프")).toBeVisible();

  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Project Alpha" })).toBeVisible();
  await expect(page.getByText("승인된 프로젝트 활동")).toBeVisible();
});
