import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";

const workspaceRoot = path.resolve(__dirname, "..");

test("dashboard calendar does not auto-select the earliest synced event on refresh", async () => {
  const source = await readFile(path.join(workspaceRoot, "src/app/dashboard/page.tsx"), "utf8");

  expect(source).not.toContain("firstEventDate");
  expect(source).not.toContain("setVisibleMonth(firstDayOfMonth(new Date(`${firstEventDate}T00:00:00+09:00`)))");
});
