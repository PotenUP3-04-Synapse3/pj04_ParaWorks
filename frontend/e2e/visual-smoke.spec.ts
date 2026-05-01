import { expect, request, test } from "@playwright/test";

const backendBaseURL = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
const pages = [
  { path: "/dashboard", heading: "오늘의 업무 흐름" },
  { path: "/messages", heading: "메신저" },
  { path: "/review", heading: "검토 큐" },
  { path: "/knowledge", heading: "승인된 회사 메모리" },
  { path: "/integrations", heading: "연동과 에이전트 도구" },
  { path: "/agent-runs", heading: "AI 실행 관측" },
  { path: "/search", heading: "회사 메모리에 질문하기" },
  { path: "/login", heading: "로그인" },
  { path: "/admin", heading: "관리자 콘솔" },
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
    expect(bodyText).not.toContain("Application error");
    expect(bodyText).not.toContain('"detail":"Not Found"');
    expect(bodyText).not.toContain("{\"detail\"");
  });
}

test("integrations page keeps all connector cards when OAuth status endpoints are optional", async ({ page }) => {
  await page.goto("/integrations");

  await expect(page.getByRole("heading", { name: "Slack" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Gmail" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Google Drive" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Google Calendar" })).toBeVisible();
});

test("theme toggle switches between dark and light glass modes", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "라이트 모드" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "다크 모드" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("sidebar search submits to the company memory search page", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes("mobile"), "desktop sidebar search is hidden on mobile");

  await page.goto("/integrations");
  await page.getByTestId("sidebar-global-search-input").fill("Redis queue state");
  await page.getByTestId("sidebar-global-search-input").press("Enter");

  await expect(page).toHaveURL(/\/search\?q=Redis\+queue\+state/);
  await expect(page.locator("#query")).toHaveValue("Redis queue state");
});

test("top search submits to the company memory search page", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes("mobile"), "desktop top search is hidden on mobile");

  await page.goto("/dashboard");
  await page.getByTestId("top-global-search-input").fill("PostgreSQL durable record");
  await page.getByTestId("top-global-search-input").press("Enter");

  await expect(page).toHaveURL(/\/search\?q=PostgreSQL\+durable\+record/);
  await expect(page.locator("#query")).toHaveValue("PostgreSQL durable record");
});

test("demo login switches the active API user", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "로그인" })).toBeVisible();
  await page.getByRole("button", { name: "이 계정으로 로그인" }).first().click();
  await expect(page.getByText("ParaWorks Admin 계정으로 전환되었습니다.")).toBeVisible();

  const storedUser = await page.evaluate(() => window.localStorage.getItem("paraworks-demo-user"));
  expect(storedUser).toBe("demo-admin");
});

test("admin console is blocked for employee accounts", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "employee-soyeon"));
  await page.goto("/admin");

  await expect(page.getByRole("heading", { name: "관리자 권한 필요" })).toBeVisible();
  await expect(page.getByRole("link", { name: "관리자 계정으로 로그인" })).toBeVisible();
});

test("admin console lists demo employees and permission levels", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/admin");

  await expect(page.getByRole("heading", { name: "관리자 콘솔" })).toBeVisible();
  await expect(page.getByText("admin@paraworks.com")).toBeVisible();
  await expect(page.getByText("mina@paraworks.com")).toBeVisible();
  await expect(page.getByText("soyeon@paraworks.com")).toBeVisible();
  await expect(page.getByText("restricted").first()).toBeVisible();
});

test("shell chrome uses distinct theme tokens across viewport modes", async ({ page }, testInfo) => {
  const isMobile = testInfo.project.name.includes("mobile");
  const shellSelector = isMobile ? "header.md\\:hidden .liquid-surface" : "aside.shell-rail";

  await page.addInitScript((theme) => window.localStorage.setItem("paraworks-theme", theme), "dark");
  await page.goto("/integrations");

  const darkStyle = await page.locator(shellSelector).evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      color: style.color,
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
    };
  });

  await page.getByRole("button", { name: "라이트 모드" }).click();

  const lightStyle = await page.locator(shellSelector).evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      color: style.color,
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
    };
  });

  expect(lightStyle.color).not.toBe(darkStyle.color);
  expect(lightStyle.backgroundColor).not.toBe(darkStyle.backgroundColor);
  expect(lightStyle.borderColor).not.toBe(darkStyle.borderColor);

  if (!isMobile) {
    const inactiveLinkColor = await page.locator("aside nav a:not(.liquid-segment-active)").first().evaluate((element) => {
      return window.getComputedStyle(element).color;
    });
    expect(inactiveLinkColor).not.toBe("rgba(255, 255, 255, 0.7)");
  }
});

test("integration sync shows connector counts", async ({ page }) => {
  await page.goto("/integrations");
  await page.getByRole("button", { name: "동기화" }).first().click();

  const syncMetrics = page.getByTestId("sync-result-metrics");
  await expect(syncMetrics.getByText("Fetched", { exact: true })).toBeVisible();
  await expect(syncMetrics.getByText("Review items", { exact: true })).toBeVisible();
  await expect(syncMetrics.getByText("Skipped", { exact: true })).toBeVisible();
});

test("integrations page shows Slack OAuth connection status without secrets", async ({ page }) => {
  await page.goto("/integrations");

  await expect(page.locator('[data-testid="slack-oauth-status"]')).toBeVisible();
  await expect(page.getByTestId("slack-runtime-status")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("xoxb-");
  expect(bodyText).not.toContain("client-secret");
  expect(bodyText).not.toContain("token_ref");
});

test("Slack card keeps OAuth install outside primary action row", async ({ page }) => {
  await page.goto("/integrations");

  const slackActions = page.getByTestId("slack-card-actions");
  await expect(slackActions.getByRole("button", { name: "동기화" })).toBeVisible();
  await expect(slackActions.getByRole("button", { name: "Slack Agent 실행" })).toBeVisible();
  await expect(slackActions.getByRole("button", { name: "Slack 연결" })).toHaveCount(0);
});

test("Slack OAuth callback route renders a safe local error without secrets", async ({ page }) => {
  await page.goto("/integrations/slack/callback");

  await expect(page.getByRole("heading", { name: "Slack 연결 확인" })).toBeVisible();
  await expect(page.getByText("Slack 연결 정보를 확인할 수 없습니다.")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("xoxb-");
  expect(bodyText).not.toContain("client-secret");
  expect(bodyText).not.toContain("token_ref");
});

test("Slack OAuth status shows reconnect CTA when the local credential is missing", async ({ page }) => {
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          connector_type: "slack",
          workspace_id: "T123",
          workspace_name: "ParaWorks Demo",
          status: "connected",
          credential_status: "missing",
          masked_bot_token: "xoxb...demo",
          scopes: ["channels:history"],
        },
      ],
    });
  });
  await page.route("**/api/v1/integrations/slack/oauth/install-url", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: "slack",
        configured: true,
        install_url: "https://slack.com/oauth/v2/authorize?client_id=C123",
        state: "signed-state",
        required_scopes: ["channels:history"],
      },
    });
  });

  await page.goto("/integrations");

  await expect(page.getByTestId("slack-oauth-workspace-name")).toHaveText("ParaWorks Demo");
  await expect(page.getByTestId("slack-oauth-workspace-name")).toHaveCSS("white-space", "nowrap");
  await expect(page.getByText("ParaWorks Demo 재연결 필요")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Slack 재연결" })).toBeVisible();
  await expect(page.getByTestId("slack-card-actions").getByRole("button", { name: "Slack 재연결" })).toHaveCount(0);
});

test("Google connector cards show OAuth readiness outside primary action rows", async ({ page }) => {
  await page.goto("/integrations");

  const connectors = [
    { type: "gmail", label: "Gmail" },
    { type: "drive", label: "Google Drive" },
    { type: "calendar", label: "Google Calendar" },
  ];

  for (const connector of connectors) {
    await expect(page.getByTestId(`${connector.type}-oauth-status`)).toBeVisible();
    await expect(
      page.getByTestId(`${connector.type}-card-actions`).getByRole("button", { name: `${connector.label} 연결` }),
    ).toHaveCount(0);
  }
  await expect(page.getByTestId("google-runtime-status")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("google-secret");
  expect(bodyText).not.toContain("refresh-token");
  expect(bodyText).not.toContain("token_ref");
});

test("Gmail and Google Drive cards show connect CTAs when OAuth is configured", async ({ page }) => {
  await page.route("**/api/v1/integrations/connections", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  for (const connectorType of ["gmail", "drive"]) {
    await page.route(`**/api/v1/integrations/${connectorType}/oauth/install-url`, async (route) => {
      await route.fulfill({
        contentType: "application/json",
        json: {
          connector_type: connectorType,
          configured: true,
          install_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=G123&state=${connectorType}-state`,
          state: `${connectorType}-state`,
          required_scopes: [`https://www.googleapis.com/auth/${connectorType}.readonly`],
        },
      });
    });
  }

  await page.goto("/integrations");

  await expect(page.getByTestId("gmail-oauth-status").getByRole("button", { name: "Gmail 연결" })).toBeVisible();
  await expect(page.getByTestId("drive-oauth-status").getByRole("button", { name: "Google Drive 연결" })).toBeVisible();
  await expect(page.getByTestId("gmail-card-actions").getByRole("button", { name: "Gmail 연결" })).toHaveCount(0);
  await expect(page.getByTestId("drive-card-actions").getByRole("button", { name: "Google Drive 연결" })).toHaveCount(0);
});

test("Google OAuth callback route renders a safe local error without secrets", async ({ page }) => {
  await page.goto("/integrations/google/callback");

  await expect(page.getByRole("heading", { name: "Google 연결 확인" })).toBeVisible();
  await expect(page.getByText("Google 연결 정보를 확인할 수 없습니다.")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("google-secret");
  expect(bodyText).not.toContain("refresh-token");
  expect(bodyText).not.toContain("token_ref");
});

test("Google OAuth callback route can complete Gmail and Drive connections", async ({ page }) => {
  await page.route("**/api/v1/integrations/google/oauth/callback?**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      json: {
        connector_type: url.searchParams.get("connector_type") ?? "gmail",
        workspace_id: "google-user-123",
        workspace_name: "para@example.com",
        status: "connected",
        credential_status: "available",
        masked_bot_token: "1//r...oken",
        scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
      },
    });
  });

  await page.goto("/integrations/google/callback?code=temporary-code&state=signed-state");

  await expect(page.getByRole("heading", { name: "Google 연결 확인" })).toBeVisible();
  await expect(page.getByText("Google 연결 완료")).toBeVisible();
  await expect(page.getByText("para@example.com 계정이 ParaWorks에 연결되었습니다.")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("refresh-token");
  expect(bodyText).not.toContain("token_ref");
});
