import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";

const workspaceRoot = path.resolve(__dirname, "..");

const utilityPages = [
  "src/app/search/page.tsx",
  "src/app/agent-runs/page.tsx",
  "src/app/integrations/page.tsx",
  "src/app/notifications/page.tsx",
  "src/app/admin/page.tsx",
];

test("utility pages opt into the dashboard-grade workspace styling scope", async () => {
  for (const pagePath of utilityPages) {
    const source = await readFile(path.join(workspaceRoot, pagePath), "utf8");
    expect(source, `${pagePath} should use the utility workspace shell`).toContain("utility-workspace");
  }

  const searchPage = await readFile(path.join(workspaceRoot, "src/app/search/page.tsx"), "utf8");
  expect(searchPage).toContain("utility-workspace-chat");

  const globals = await readFile(path.join(workspaceRoot, "src/app/globals.css"), "utf8");
  expect(globals).toContain(".utility-workspace .page-heading.reference-heading");
  expect(globals).toContain(".utility-workspace .panel.reference-panel");
  expect(globals).toContain(".utility-workspace-chat");
});

test("AI assistant keeps explicit open and collapse controls for chat history", async () => {
  const searchPage = await readFile(path.join(workspaceRoot, "src/app/search/page.tsx"), "utf8");

  expect(searchPage).toContain("data-assistant-history-open");
  expect(searchPage).toContain("data-assistant-history-collapse");
  expect(searchPage).toContain("대화 목록 펼치기");
  expect(searchPage).toContain("대화 목록 접기");
  expect(searchPage).toContain(">접기<");
  expect(searchPage).not.toContain("히스토리 접기");
  expect(searchPage).toContain("setSidebarCollapsed(false)");
  expect(searchPage).toContain("setSidebarCollapsed(true)");
});
