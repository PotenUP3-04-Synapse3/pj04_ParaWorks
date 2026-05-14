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

test("Slack sync blocks the page with a progress modal and then reports the review queue total", async ({
  page,
}) => {
  let releaseSync!: () => void;
  const syncGate = new Promise<void>((resolve) => {
    releaseSync = resolve;
  });

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
        latest_sync: null,
        latest_sync_summary: null,
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
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "slack-sync-modal-test",
        connector_type: "slack",
        status: "complete",
        created_review_items: 3,
        pending_review_count: 14,
        fetched_events: 210,
        skipped_events: 0,
        parser_status_counts: {},
        changed_source_ids: ["C123:1777600800.000100"],
        agent_generated_items: 2,
        project_assignment_items: 1,
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
  await expect(page.getByTestId("sync-result-metrics")).toContainText("검토 대기");
  await expect(page.getByTestId("sync-result-metrics")).toContainText("14");
});
