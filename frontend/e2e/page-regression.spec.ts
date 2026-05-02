import { expect, request, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const backendBaseURL = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";

const expectedAppRoutes = [
  "/",
  "/admin",
  "/agent-runs",
  "/agent-runs/[id]",
  "/dashboard",
  "/decisions",
  "/history",
  "/integrations",
  "/integrations/google/callback",
  "/integrations/slack/callback",
  "/knowledge",
  "/login",
  "/messages",
  "/notifications",
  "/review",
  "/search",
  "/timeline",
];

const staticPageTargets = [
  { name: "root redirect", path: "/", expectedUrl: /\/dashboard$/ },
  { name: "dashboard", path: "/dashboard" },
  { name: "messages", path: "/messages" },
  { name: "notifications", path: "/notifications" },
  { name: "review", path: "/review" },
  { name: "knowledge", path: "/knowledge" },
  { name: "decisions", path: "/decisions" },
  { name: "timeline", path: "/timeline" },
  { name: "history", path: "/history" },
  { name: "search", path: "/search" },
  { name: "agent runs", path: "/agent-runs" },
  { name: "integrations", path: "/integrations" },
  { name: "slack callback", path: "/integrations/slack/callback" },
  { name: "google callback", path: "/integrations/google/callback" },
  { name: "admin", path: "/admin" },
  { name: "login", path: "/login" },
];

const themeModes = ["dark", "light"] as const;

test("route inventory covers every app page", () => {
  expect(discoverAppPageRoutes()).toEqual(expectedAppRoutes);
});

for (const themeMode of themeModes) {
  for (const target of staticPageTargets) {
    test(`${target.name} renders cleanly in ${themeMode} mode`, async ({ page }) => {
      const monitor = monitorPageErrors(page);
      await setThemeBeforeNavigation(page, themeMode);

      await page.goto(target.path, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);

      if (target.expectedUrl) {
        await expect(page).toHaveURL(target.expectedUrl);
      }
      await assertPageHealth(page);
      expect(monitor.errors()).toEqual([]);
    });
  }
}

for (const themeMode of themeModes) {
  test(`agent run detail renders cleanly in ${themeMode} mode`, async ({ page }) => {
    const runId = await latestAgentRunId();
    test.skip(runId === null, "agent run detail needs at least one seeded AgentRun record");

    const monitor = monitorPageErrors(page);
    await setThemeBeforeNavigation(page, themeMode);

    await page.goto(`/agent-runs/${runId}`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);

    await assertPageHealth(page);
    await expect(page.getByText("Agent Run")).toBeVisible();
    expect(monitor.errors()).toEqual([]);
  });
}

async function latestAgentRunId(): Promise<number | null> {
  const api = await request.newContext({ baseURL: backendBaseURL });
  try {
    const response = await api.get("/api/v1/agent-runs");
    if (!response.ok()) {
      return null;
    }
    const payload = (await response.json()) as { recent_runs?: Array<{ id?: number }> };
    return payload.recent_runs?.[0]?.id ?? null;
  } finally {
    await api.dispose();
  }
}

function monitorPageErrors(page: Page) {
  const errors: string[] = [];

  page.on("console", (message) => {
    if (message.type() !== "error") {
      return;
    }
    const text = message.text();
    if (text.includes("favicon.ico")) {
      return;
    }
    errors.push(text);
  });
  page.on("pageerror", (error) => errors.push(error.message));

  return { errors: () => errors };
}

async function setThemeBeforeNavigation(page: Page, themeMode: (typeof themeModes)[number]) {
  await page.addInitScript((theme) => {
    window.localStorage.setItem("paraworks-theme", theme);
  }, themeMode);
}

async function assertPageHealth(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-theme", /^(dark|light)$/);
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/Application error|Unhandled Runtime Error|500 Internal Server Error/);
  await expect(page.locator("body")).not.toContainText(/"detail":"Not Found"|\{"detail"/);

  const metrics = await page.evaluate(() => {
    const main = document.querySelector("main");
    const mainRect = main?.getBoundingClientRect();
    return {
      bodyTextLength: document.body.innerText.trim().length,
      horizontalOverflow: Math.ceil(document.documentElement.scrollWidth - document.documentElement.clientWidth),
      mainHeight: mainRect?.height ?? 0,
      visibleGlassCount: Array.from(
        document.querySelectorAll(".liquid-surface, .workspace-glass-card, .integration-glass-card, .bg-white"),
      ).filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      }).length,
    };
  });

  expect(metrics.bodyTextLength).toBeGreaterThan(40);
  expect(metrics.mainHeight).toBeGreaterThan(80);
  expect(metrics.horizontalOverflow).toBeLessThanOrEqual(2);
  expect(metrics.visibleGlassCount).toBeGreaterThan(0);
}

function discoverAppPageRoutes() {
  const appDir = path.join(process.cwd(), "src", "app");
  const pageFiles = collectPageFiles(appDir);
  return pageFiles.map((file) => routeFromPageFile(appDir, file)).sort();
}

function collectPageFiles(directory: string): string[] {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return collectPageFiles(entryPath);
    }
    return entry.name === "page.tsx" ? [entryPath] : [];
  });
}

function routeFromPageFile(appDir: string, file: string) {
  const routeDir = path.relative(appDir, path.dirname(file));
  if (!routeDir) {
    return "/";
  }
  return `/${routeDir.split(path.sep).join("/")}`;
}
