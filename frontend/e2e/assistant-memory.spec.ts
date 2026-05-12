import { expect, test } from "@playwright/test";

test("search page behaves as a persisted AI assistant without cost labels", async ({ page }) => {
  const conversations = [
    {
      id: 10,
      title: "Redis 질문",
      summary: "Redis 작업 상태 대화",
      created_at: "2026-05-12T01:00:00+00:00",
      updated_at: "2026-05-12T01:00:00+00:00",
    },
  ];
  const messages = [
    {
      id: 100,
      conversation_id: 10,
      role: "assistant",
      content: "Redis는 일시적인 작업 상태 공유에 사용됩니다.",
      citations: [
        {
          source_id: "gmail-redis",
          source_url: "https://gmail.mock/redis",
          source_type: "gmail",
          permission_level: "internal",
          source_snippet: "Redis 작업 상태 근거",
          relevance_score: 1,
          matched_terms: ["redis"],
        },
      ],
      source_ids: ["gmail-redis"],
      source_links: ["https://gmail.mock/redis"],
      source_snippets: ["Redis 작업 상태 근거"],
      permission_level: "internal",
      hidden_match_count: 0,
      permission_notice: null,
      agent_run_id: 77,
      metadata: {},
      created_at: "2026-05-12T01:00:00+00:00",
    },
  ];

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "employee-mina",
          email: "mina@paraworks.com",
          role: "reviewer",
          permission_levels: ["public", "internal"],
          name: "Kim Mina",
          title: "Product Manager",
          department: "Product",
        },
      },
    });
  });

  await page.route("**/api/v1/assistant/conversations", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", json: { conversations } });
      return;
    }

    await route.fulfill({ contentType: "application/json", json: { conversation: conversations[0] } });
  });

  await page.route("**/api/v1/assistant/conversations/10/messages", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        json: { conversation: conversations[0], messages },
      });
      return;
    }

    await route.fulfill({
      contentType: "application/json",
      json: {
        conversation: conversations[0],
        user_message: {
          id: 101,
          conversation_id: 10,
          role: "user",
          content: "그 다음 할 일은?",
          citations: [],
          source_ids: [],
          source_links: [],
          source_snippets: [],
          permission_level: null,
          hidden_match_count: 0,
          permission_notice: null,
          agent_run_id: null,
          metadata: {},
          created_at: "2026-05-12T01:01:00+00:00",
        },
        assistant_message: {
          ...messages[0],
          id: 102,
          content: "다음 단계는 회의 전 Redis 작업 상태를 공유하는 것입니다.",
        },
      },
    });
  });

  await page.route("**/api/v1/rag/indexing/summary", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        state_counts: { indexed: 1 },
        latest_jobs: [
          {
            job_id: "job-1",
            connector_type: "rag",
            status: "complete",
            message: "indexed",
            progress_pct: 100,
            indexed_count: 1,
            skipped_count: 0,
            saved_embedding_calls: 0,
            updated_at: "2026-05-12T01:00:00+00:00",
          },
        ],
        cost_policy: {
          embedding_model: "text-embedding-3-small",
          embedding_input_cost_per_1m_tokens: 0.02,
          max_estimated_embedding_cost_usd: 0.001,
          preflight_budget_gate: true,
          incremental_hash_skip: true,
        },
      },
    });
  });

  await page.goto("/search");

  await expect(page.getByRole("heading", { level: 1, name: "AI 비서와 대화" })).toBeVisible();
  await expect(page.getByText("Redis는 일시적인 작업 상태 공유에 사용됩니다.")).toBeVisible();
  await page.getByRole("button", { name: "근거 보기" }).click();
  await expect(page.getByText("Redis 작업 상태 근거").first()).toBeVisible();

  await page.getByRole("textbox", { name: "AI 비서에게 질문" }).fill("그 다음 할 일은?");
  await page.getByRole("button", { name: "보내기" }).click();
  await expect(page.getByText("다음 단계는 회의 전 Redis 작업 상태를 공유하는 것입니다.")).toBeVisible();

  const body = page.locator("body");
  await expect(body).not.toContainText("token");
  await expect(body).not.toContainText("cache");
  await expect(body).not.toContainText("$");
  await expect(body).not.toContainText("토큰");
  await expect(body).not.toContainText("비용");
  await expect(body).not.toContainText("캐시");
});
