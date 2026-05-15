import { expect, test } from "@playwright/test";

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

test("Integrations page keeps every connector card visible while manifests are loading", async ({
  page,
}) => {
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
  await page.route("**/api/v1/integrations", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: 0,
        source_counts: { slack: 0, gmail: 0, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/integrations/*/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "unknown",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/*/runtime-status", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "unknown",
        mode: "mock",
        connection_status: "disconnected",
        credential_status: "missing",
        account_name: null,
        latest_sync: null,
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");

  await expect(page.getByRole("heading", { name: "Slack" })).toBeVisible({ timeout: 500 });
  await expect(page.getByRole("heading", { name: "Gmail" })).toBeVisible({ timeout: 500 });
  await expect(page.getByRole("heading", { name: "Google Drive" })).toBeVisible({ timeout: 500 });
  await expect(page.getByRole("heading", { name: "Google Calendar" })).toBeVisible({ timeout: 500 });
});

test("Slack sync blocks the page with a progress modal and then reports the review queue total", async ({
  page,
}) => {
  let releaseSync!: () => void;
  const syncGate = new Promise<void>((resolve) => {
    releaseSync = resolve;
  });
  let syncQueued = false;

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
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: 11,
        source_counts: { slack: 210, gmail: 0, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/runtime-status", async (route) => {
    const latestSync = syncQueued
      ? {
          job_id: "slack-sync-modal-test",
          status: "complete",
          message: "fetched=210 created_review_items=3 skipped_events=0 pending_review_items=14",
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
        channel_options: [
          { id: "C123", name: "C123", is_selected: true, is_configured: true },
        ],
        connection_status: "connected",
        credential_status: "available",
        latest_sync: latestSync,
        latest_sync_summary: syncQueued
          ? { fetched_events: 210, created_review_items: 3, skipped_events: 0 }
          : null,
        last_error: null,
        agent_bridge: {
          slack_source_count: 210,
          pending_review_count: 11,
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
  await page.route("**/api/v1/integrations/{gmail,drive,calendar}/**", async (route) => {
    await route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not configured" } });
  });
  await page.route("**/api/v1/integrations/slack/sync", async (route) => {
    await syncGate;
    syncQueued = true;
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "slack-sync-modal-test",
        connector_type: "slack",
        status: "queued",
        created_review_items: 0,
        pending_review_count: 11,
        fetched_events: 0,
        skipped_events: 0,
        parser_status_counts: {},
        changed_source_ids: [],
        agent_generated_items: 0,
        project_assignment_items: 0,
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("slack-card-actions")).toBeVisible();

  await page.getByTestId("slack-card-actions").getByRole("button", { name: "동기화" }).click();

  const modal = page.getByTestId("sync-progress-modal");
  await expect(modal).toBeVisible();
  await expect(modal).toContainText("Slack 동기화 중");
  await expect(modal).toContainText("원본 수집과 AI 분석을 진행 중입니다");
  await expect(page.getByTestId("sync-progress-backdrop")).toBeVisible();
  await expect(page.getByTestId("sync-progress-backdrop")).toHaveAttribute("aria-modal", "true");
  await expect(page.getByTestId("slack-card-actions").getByRole("button", { name: "동기화 중" })).toBeDisabled();

  releaseSync();

  await expect(modal).toContainText("동기화 완료");
  await expect(modal).toContainText("검토 대기 14개");
  await page.getByRole("button", { name: "닫기", exact: true }).click();
  await expect(modal).toBeHidden();
  await expect(page.getByTestId("sync-result-metrics")).toHaveCount(0);
  await expect(page.getByTestId("source-operations-panel")).toBeVisible();
  await expect(page.getByTestId("source-operation-slack-count")).toContainText("210");
  await expect(page.getByTestId("source-operations-panel")).not.toContainText("%");
  await expect(page.getByTestId("slack-runtime-status")).toHaveCount(0);
});

test("Slack sync recovers when the final POST response is lost after the backend job completes", async ({
  page,
}) => {
  let syncAttempted = false;

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
          cost_policy: "changed sources only",
        },
      ],
    });
  });
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: 11,
        source_counts: { slack: 205, gmail: 0, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/runtime-status", async (route) => {
    const latestSync = syncAttempted
      ? {
          job_id: "slack-lost-response-test",
          status: "complete",
          message: "fetched=205 created_review_items=11 skipped_events=0 pending_review_items=11",
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
        channel_options: [
          { id: "C123", name: "C123", is_selected: true, is_configured: true },
        ],
        connection_status: "connected",
        credential_status: "available",
        latest_sync: latestSync,
        latest_sync_summary: syncAttempted
          ? { fetched_events: 205, created_review_items: 11, skipped_events: 0 }
          : null,
        last_error: null,
        agent_bridge: {
          slack_source_count: 205,
          pending_review_count: 11,
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
  await page.route("**/api/v1/integrations/{gmail,drive,calendar}/**", async (route) => {
    await route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not configured" } });
  });
  await page.route("**/api/v1/integrations/slack/sync", async (route) => {
    syncAttempted = true;
    await route.fulfill({
      status: 500,
      contentType: "text/plain",
      body: "Internal Server Error",
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");
  await page.waitForLoadState("networkidle");

  await page.getByTestId("slack-card-actions").getByRole("button").first().click();

  const modal = page.getByTestId("sync-progress-modal");
  await expect(modal).toBeVisible();
  await expect(modal).toContainText("11", { timeout: 10_000 });
  await expect(modal).not.toContainText("Internal Server Error");
  await page.getByRole("button", { name: "닫기", exact: true }).click();
  await expect(page.getByTestId("sync-result-metrics")).toHaveCount(0);
  await expect(page.getByTestId("source-operations-panel")).toBeVisible();
});

test("Slack sync polling timeout stays in background-running state instead of failure", async ({
  page,
}) => {
  await page.clock.install();

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
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: 8,
        source_counts: { slack: 207, gmail: 0, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/runtime-status", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        mode: "live",
        configured_channel_ids: ["C123"],
        selected_channel_ids: ["C123"],
        channel_options: [
          { id: "C123", name: "C123", is_selected: true, is_configured: true },
        ],
        connection_status: "connected",
        credential_status: "available",
        latest_sync: {
          job_id: "slack-long-running-test",
          status: "running",
          message: "agent_review=running",
          progress_pct: 75,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        latest_sync_summary: { fetched_events: 207, created_review_items: 0, skipped_events: 0 },
        last_error: null,
        agent_bridge: {
          slack_source_count: 207,
          pending_review_count: 8,
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
  await page.route("**/api/v1/integrations/{gmail,drive,calendar}/**", async (route) => {
    await route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not configured" } });
  });
  await page.route("**/api/v1/integrations/slack/sync", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "slack-long-running-test",
        connector_type: "slack",
        status: "queued",
        created_review_items: 0,
        pending_review_count: 8,
        fetched_events: 0,
        skipped_events: 0,
        parser_status_counts: {},
        changed_source_ids: [],
        agent_generated_items: 0,
        project_assignment_items: 0,
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");
  await page.waitForLoadState("networkidle");

  await expect(page.getByTestId("runtime-sync-progress")).toHaveCount(0);
  await expect(page.getByTestId("source-operations-panel")).toBeVisible();

  await page.getByTestId("slack-card-actions").getByRole("button", { name: "동기화" }).click();
  const modal = page.getByTestId("sync-progress-modal");
  await expect(modal).toBeVisible();

  for (let attempt = 0; attempt < 95; attempt += 1) {
    await page.clock.fastForward(1_500);
    await new Promise((resolve) => setTimeout(resolve, 0));
  }

  await expect(modal).toContainText("Slack 동기화 중");
  await expect(modal).toContainText("백그라운드에서 계속 진행 중입니다");
  await expect(modal.getByTestId("sync-progress-percent")).toContainText("75%");
  await expect(modal).not.toContainText("동기화 실패");

  await page.getByRole("button", { name: "백그라운드에서 계속 진행" }).click();
  await expect(modal).toBeHidden();

  await expect(page.getByTestId("background-sync-progress")).toHaveCount(0);
  await expect(page.getByTestId("source-operations-panel")).toBeVisible();
});

test("Gmail sync uses async job polling so the modal reflects runtime progress", async ({
  page,
}) => {
  await page.clock.install();
  let syncQueued = false;
  let syncCompleted = false;
  let postedBody: unknown;

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
  await page.route("**/api/v1/integrations", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          type: "gmail",
          display_name: "Gmail",
          mode: "live",
          status: "ready",
          auth_type: "oauth",
          required_scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          sync_strategy: "incremental",
          cost_policy: "changed messages only",
        },
      ],
    });
  });
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        pending_review_count: syncCompleted ? 9 : 7,
        source_counts: { slack: 0, gmail: 23, drive: 0, calendar: 0, other: 0 },
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/slack/runtime-status", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        mode: "live",
        configured_channel_ids: [],
        selected_channel_ids: [],
        channel_options: [],
        connection_status: "disconnected",
        credential_status: "missing",
        latest_sync: null,
        latest_sync_summary: null,
        last_error: null,
        agent_bridge: {
          slack_source_count: 0,
          pending_review_count: 0,
          ready_for_agent_test: false,
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
  await page.route("**/api/v1/integrations/{drive,calendar}/**", async (route) => {
    await route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not configured" } });
  });
  await page.route("**/api/v1/integrations/gmail/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "gmail",
        configured: false,
        install_url: null,
        state: null,
        required_scopes: [],
      },
    });
  });
  await page.route("**/api/v1/integrations/gmail/runtime-status", async (route) => {
    const latestSync = syncQueued
      ? {
          job_id: "gmail-async-progress-test",
          status: syncCompleted ? "complete" : "running",
          message: syncCompleted
            ? "fetched=23 created_review_items=2 skipped_events=0 pending_review_items=9"
            : "fetched=23 agent_review=running skipped_events=0",
          progress_pct: syncCompleted ? 100 : 75,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
      : null;

    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "gmail",
        mode: "live",
        connection_status: "connected",
        credential_status: "available",
        account_name: "para@example.com",
        latest_sync: latestSync,
        cost_policy: {
          status_lookup_triggers_sync: false,
          status_lookup_triggers_llm: false,
        },
      },
    });
  });
  await page.route("**/api/v1/integrations/gmail/sync", async (route) => {
    postedBody = route.request().postDataJSON();
    syncQueued = true;
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "gmail-async-progress-test",
        connector_type: "gmail",
        status: "queued",
        created_review_items: 0,
        pending_review_count: 7,
        fetched_events: 0,
        skipped_events: 0,
        parser_status_counts: {},
        changed_source_ids: [],
        agent_generated_items: 0,
        project_assignment_items: 0,
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/integrations");
  await page.waitForLoadState("networkidle");

  await page.getByTestId("gmail-card-actions").getByRole("button").first().click();
  const modal = page.getByTestId("sync-progress-modal");

  await expect(modal).toBeVisible();
  expect(postedBody).toMatchObject({ run_async: true });
  await expect(modal.getByTestId("sync-progress-percent")).not.toContainText("75%");
  await page.clock.fastForward(6_000);
  await expect(modal.getByTestId("sync-progress-percent")).toContainText("75%");

  syncCompleted = true;
  await page.clock.fastForward(1_500);
  await expect(modal.getByTestId("sync-progress-percent")).toContainText("100%");
});
