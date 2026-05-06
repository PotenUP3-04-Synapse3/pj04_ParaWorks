import { expect, test } from "@playwright/test";

test("admin demo login can open agent runs observability", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();

  const adminCard = page.locator("article").filter({ hasText: "admin@paraworks.com" }).first();
  await adminCard.getByRole("button", { name: "Use this account" }).click();
  await expect(page.getByText("ParaWorks Admin is now active.")).toBeVisible();

  await page.goto("/agent-runs");

  await expect(page.getByText("Agent Operations")).toBeVisible();
  await expect(page.getByText("Admin permission required")).not.toBeVisible();
});
