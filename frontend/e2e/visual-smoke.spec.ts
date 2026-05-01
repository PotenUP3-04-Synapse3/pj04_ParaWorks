import { expect, request, test } from "@playwright/test";

const backendBaseURL = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
const pages = [
  { path: "/dashboard", heading: "오늘의 업무 흐름" },
  { path: "/integrations", heading: "연동과 에이전트 도구" },
  { path: "/agent-runs", heading: "AI 실행 관측" },
  { path: "/search", heading: "회사 메모리에 질문하기" },
];

test.beforeAll(async () => {
  const api = await request.newContext({ baseURL: backendBaseURL });
  try {
    await api.post("/api/v1/integrations/slack/sync");
    await api.post("/api/v1/integrations/gmail/sync");
    await api.post("/api/v1/rag/reindex/jobs");
  } finally {
    await api.dispose();
  }
});

for (const target of pages) {
  test(`${target.path} renders Korean workspace UI without mojibake`, async ({ page }) => {
    await page.goto(target.path);
    await expect(page.getByRole("heading", { name: target.heading })).toBeVisible();

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("�");
    expect(bodyText).not.toContain("?꾩");
    expect(bodyText).not.toContain("?ㅽ");
    expect(bodyText).not.toContain("?덉");
  });
}

test("integration sync shows connector counts", async ({ page }) => {
  await page.goto("/integrations");
  await page.getByRole("button", { name: "동기화" }).first().click();

  await expect(page.getByText("Fetched")).toBeVisible();
  await expect(page.getByText("Review items")).toBeVisible();
  await expect(page.getByText("Skipped")).toBeVisible();
});

test("integrations page shows Slack OAuth connection status without secrets", async ({ page }) => {
  await page.goto("/integrations");

  await expect(page.locator('[data-testid="slack-oauth-status"]')).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("xoxb-");
  expect(bodyText).not.toContain("client-secret");
  expect(bodyText).not.toContain("token_ref");
});
