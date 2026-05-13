import { expect, test } from "@playwright/test";

test("search page behaves like a persisted assistant with compact history and folded evidence", async ({ page }) => {
  const usedConversation = {
    id: 10,
    title: "Redis 작업 상태",
    summary: "이 요약 문장은 히스토리 목록에 직접 노출되면 안 됩니다.",
    created_at: "2026-05-12T01:00:00+00:00",
    updated_at: "2026-05-12T01:00:00+00:00",
  };
  const emptyConversation = {
    id: 11,
    title: "새 대화",
    summary: null,
    created_at: "2026-05-12T01:03:00+00:00",
    updated_at: "2026-05-12T01:03:00+00:00",
  };
  const latestConversation = {
    id: 12,
    title: "기획팀 회의",
    summary: "최신 대화 요약입니다.",
    created_at: "2026-05-12T01:05:00+00:00",
    updated_at: "2026-05-12T01:05:00+00:00",
  };
  const manyCitations = Array.from({ length: 12 }, (_, index) => ({
    source_id: `gmail-redis-${index + 1}`,
    source_url: `https://gmail.mock/redis-${index + 1}`,
    source_type: "gmail",
    permission_level: "internal",
    source_snippet: `세부 근거 ${index + 1}: Redis 작업 상태 기록입니다.`,
    relevance_score: 1 - index * 0.02,
    matched_terms: ["redis"],
  }));
  const messages = [
    {
      id: 100,
      conversation_id: 10,
      role: "assistant",
      content: "**Redis**는 임시 작업 상태를 빠르게 공유하는 용도로 쓰입니다.\n\n- 큐 진행 상황 공유\n- PostgreSQL 기록 보존",
      citations: manyCitations,
      source_ids: manyCitations.map((citation) => citation.source_id),
      source_links: manyCitations.map((citation) => citation.source_url),
      source_snippets: manyCitations.map((citation) => citation.source_snippet),
      permission_level: "internal",
      hidden_match_count: 0,
      permission_notice: null,
      agent_run_id: 77,
      metadata: {},
      created_at: "2026-05-12T01:00:00+00:00",
    },
  ];
  let createConversationPostCount = 0;

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
      await route.fulfill({
        contentType: "application/json",
        json: { conversations: [latestConversation, emptyConversation, usedConversation] },
      });
      return;
    }

    createConversationPostCount += 1;
    await route.fulfill({ contentType: "application/json", json: { conversation: emptyConversation } });
  });

  await page.route("**/api/v1/assistant/conversations/10/messages", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { conversation: usedConversation, messages },
    });
  });

  await page.route("**/api/v1/assistant/conversations/11/messages", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        json: { conversation: emptyConversation, messages: [] },
      });
      return;
    }

    await route.fulfill({
      contentType: "application/json",
      json: {
        conversation: { ...emptyConversation, title: "기획팀 회의 안내" },
        user_message: {
          id: 101,
          conversation_id: 11,
          role: "user",
          content: "기획팀 회의 일정을 정리해줘",
          citations: [],
          source_ids: [],
          source_links: [],
          source_snippets: [],
          permission_level: null,
          hidden_match_count: 0,
          permission_notice: null,
          agent_run_id: null,
          metadata: {},
          created_at: "2026-05-12T01:04:00+00:00",
        },
        assistant_message: {
          id: 102,
          conversation_id: 11,
          role: "assistant",
          content: "기획팀 회의는 목요일 오전 일정으로 정리하면 좋습니다.",
          citations: [],
          source_ids: [],
          source_links: [],
          source_snippets: [],
          permission_level: "internal",
          hidden_match_count: 0,
          permission_notice: null,
          agent_run_id: 78,
          metadata: {},
          created_at: "2026-05-12T01:04:01+00:00",
        },
      },
    });
  });

  await page.route("**/api/v1/assistant/conversations/12/messages", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { conversation: latestConversation, messages: [] },
    });
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const expectedRoutes = new Set([
      "GET /api/v1/auth/me",
      "GET /api/v1/assistant/conversations",
      "POST /api/v1/assistant/conversations",
      "GET /api/v1/assistant/conversations/10/messages",
      "GET /api/v1/assistant/conversations/11/messages",
      "GET /api/v1/assistant/conversations/12/messages",
      "POST /api/v1/assistant/conversations/11/messages",
    ]);

    if (expectedRoutes.has(`${request.method()} ${url.pathname}`)) {
      await route.fallback();
      return;
    }

    throw new Error(`Unexpected API call in assistant memory test: ${request.method()} ${url.pathname}`);
  });

  await page.goto("/search");

  await expect(page.getByText("회사 기억 준비 중")).toHaveCount(0);
  await expect(page.getByText("ParaWorks RAG")).toHaveCount(0);
  const history = page.getByRole("complementary", { name: "대화 목록" });
  const historyItems = page.getByLabel("대화 히스토리");
  await expect(history).toHaveAttribute("data-expanded", "true");
  await page.getByRole("button", { name: "대화 목록 접기" }).click();
  await expect(history).toHaveAttribute("data-expanded", "false");
  await expect(history).toHaveClass(/w-\[72px\]/);
  await page.getByRole("button", { name: "대화 목록 펼치기" }).click();
  await expect(history).toHaveAttribute("data-expanded", "true");
  await expect(historyItems.getByRole("button").nth(0)).toContainText("기획팀 회의");
  await history.getByRole("button", { name: "Redis 작업 상태" }).click();
  await expect(historyItems.getByRole("button").nth(0)).toContainText("기획팀 회의");
  await expect(history).toContainText("Redis 작업 상태");
  await expect(history).not.toContainText("이 요약 문장");
  await expect(page.locator("strong").filter({ hasText: "Redis" })).toBeVisible();
  await expect(page.getByText("큐 진행 상황 공유")).toBeVisible();
  await expect(page.locator(".badge").filter({ hasText: "AI 비서" })).toHaveCount(0);
  await expect(page.getByText("internal", { exact: true })).toHaveCount(0);
  await expect(page.getByText("나", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "복사" })).toBeVisible();
  const assistantInput = page.getByRole("form", { name: "AI 비서 입력" });
  await expect(assistantInput).toHaveClass(/bg-white\/80/);
  await expect(assistantInput).not.toHaveClass(/border-t/);

  await expect(page.getByText("세부 근거 1: Redis 작업 상태 기록입니다.")).toBeHidden();
  await page.getByRole("button", { name: /근거와 출처 12개/ }).click();
  await expect(page.getByText("세부 근거 12: Redis 작업 상태 기록입니다.")).toBeVisible();

  await page.getByRole("button", { name: "새 대화 만들기" }).click();
  await page.getByRole("button", { name: "새 대화 만들기" }).click();
  await expect(page.getByLabel("대화 목록").getByText("새 대화")).toHaveCount(1);
  expect(createConversationPostCount).toBe(0);

  await page.getByRole("button", { name: "기획팀 회의 일정을 정리해줘" }).click();
  await expect(page.getByText("기획팀 회의는 목요일 오전 일정으로 정리하면 좋습니다.")).toBeVisible();
  const userQuestionBubble = page.locator("article").filter({ hasText: "기획팀 회의 일정을 정리해줘" });
  await expect(userQuestionBubble.getByText("기획팀 회의 일정을 정리해줘")).toBeVisible();
  await expect(userQuestionBubble.locator(".rounded-full.bg-\\[var\\(--primary\\)\\].px-3.py-2")).toBeVisible();
  await expect(page.getByRole("button", { name: "최근 결정된 사항만 요약해줘" })).toHaveClass(/bg-\[var\(--primary\)\]/);

  const body = page.locator("body");
  await expect(body).not.toContainText(/cost|token|cache|토큰|비용|캐시/i);
  await expect(body).not.toContainText("$");
});
