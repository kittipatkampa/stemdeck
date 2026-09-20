import { test, expect } from "@playwright/test";
import { openStudio } from "./helpers.mjs";

const API = "https://api.github.com/repos/kittipatkampa/stemdeck/releases?per_page=10";
const RELEASE = "https://github.com/kittipatkampa/stemdeck/releases/tag/v9.9.9";

test("fork release discovery retains manual downloads without updater assets", async ({ page }) => {
  const githubRequests = [];
  page.on("request", (request) => {
    if (request.url().startsWith("https://api.github.com/")) githubRequests.push(request.url());
  });
  await openStudio(page, { tauri: true, updateAvailable: true });
  const card = page.locator("#notifReleaseCard");
  await expect(card).not.toHaveClass(/\bhidden\b/);
  // The notification card lives inside the initially closed notification panel.
  await card.evaluate((element) => element.click());
  await expect(page.locator("#releaseDialog")).toBeVisible();
  await expect(page.locator("#releaseDownload")).toHaveAttribute("href", RELEASE);
  await expect(page.locator("#releaseInapp")).toBeHidden();
  expect(githubRequests).toContain(API);
  expect(githubRequests.every((url) => url.startsWith(API))).toBe(true);
});

test("offline release discovery does not prevent the library from loading", async ({ page }) => {
  await openStudio(page);
  await page.route(API, (route) => route.abort("internetdisconnected"));
  await page.reload();
  await expect(page.locator(".cat-item").first()).toBeVisible();
  await expect(page.locator("#notifReleaseCard")).toBeHidden();
});
