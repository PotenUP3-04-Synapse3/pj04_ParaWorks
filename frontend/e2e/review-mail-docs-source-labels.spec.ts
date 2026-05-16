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

const sourceEvidence = (sourceType: string, index: number) => ({
  index,
  rank: index,
  source_id: `${sourceType}:source-${index}`,
  source_url: `https://${sourceType}.example/source-${index}`,
  source_type: sourceType,
  source_snippet: `${sourceType} evidence`,
  permission_level: "internal",
  confidence_score: 0.84,
  importance_score: 0,
  timestamp: null,
  author: null,
  agent_run_id: 991,
  parser_status: null,
  section_path: null,
  evidence_reason: null,
});

const reviewItem = (id: number, title: string, sourceTypes: string[]) => ({
  id,
  item_type: "history_event",
  payload: {
    title,
    summary: `${title} summary`,
    agent_name: "mail_document_agent",
    source_types: sourceTypes,
  },
  source_links: sourceTypes.map((sourceType, index) => `https://${sourceType}.example/source-${index + 1}`),
  source_snippets: sourceTypes.map((sourceType) => `${sourceType} snippet`),
  source_evidence: sourceTypes.map((sourceType, index) => sourceEvidence(sourceType, index + 1)),
  agent_run_id: 991,
  agent_run_details: {
    model_name: "fake-mail-document-agent-model",
    prompt_version: "mail-document-history:v1",
    estimated_cost_usd: 0,
    total_tokens: 0,
  },
  confidence_score: 0.84,
  permission_level: "internal",
  status: "pending_review",
  reviewer_id: null,
});

const items = [
  reviewItem(901, "Mail only candidate", ["gmail"]),
  reviewItem(902, "Docs only candidate", ["drive"]),
  reviewItem(903, "Calendar only candidate", ["calendar"]),
  reviewItem(904, "Mail docs candidate", ["gmail", "drive"]),
];

test("Review page shows Mail Docs Calendar source labels for Mail/Docs agent items", async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { user: baseUser } });
  });
  await page.route("**/api/v1/notifications", async (route) => {
    await route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } });
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { pending_review_count: items.length, source_counts: { gmail: 2, drive: 2, calendar: 1 } },
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
            group_id: "history_event:source-labels",
            title: "Source label candidates",
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            items,
            total_count: items.length,
            avg_confidence: 0.84,
          },
        ],
        items,
        total_count: items.length,
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
      json: {
        target_type: "history_event",
        can_approve: true,
        missing_required_fields: [],
        normalized_payload: { title: "Source label candidate" },
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/review");
  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("Mail", { exact: true })).toBeVisible();
  await expect(page.getByText("Docs", { exact: true })).toBeVisible();
  await expect(page.getByText("Calendar", { exact: true })).toBeVisible();
  await expect(page.getByText("Mail + Docs", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Mail/Docs Agent");
});
