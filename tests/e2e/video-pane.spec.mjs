import { test, expect } from "@playwright/test";
import { openStudio, JOB_ID } from "./helpers.mjs";

test.describe("karaoke video pane", () => {
  test("video pane and controls appear for a track with video", async ({ page }) => {
    await openStudio(page, { tauri: true });
    await page.locator(`.cat-item[data-id="${JOB_ID}"]`).click();

    const pane = page.locator("#dawVideoPane");
    await expect(pane).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#dawVideo")).toBeVisible();
    await expect(page.locator("#dawVideoFullscreen")).toBeVisible();
    await expect(page.locator("#dawVideoResize")).toBeVisible();
    await expect(page.locator("#panelVideoToggle")).toBeVisible();
  });

  test("video panel toggle collapses the pane", async ({ page }) => {
    await openStudio(page, { tauri: true });
    await page.locator(`.cat-item[data-id="${JOB_ID}"]`).click();
    await expect(page.locator("#dawVideoPane")).toBeVisible({ timeout: 15000 });

    await page.locator("#panelVideoToggle").click();
    await expect(page.locator("#dawVideoPane")).toBeHidden();

    await page.locator("#panelVideoToggle").click();
    await expect(page.locator("#dawVideoPane")).toBeVisible();
  });

  test("audio-only sibling has no video pane", async ({ page }) => {
    await openStudio(page, { tauri: true });
    await page.locator('.cat-item[data-id="e2e0cafebabe"]').click();
    await expect(page.locator("#dawVideoPane")).toBeHidden({ timeout: 15000 });
    await expect(page.locator("#panelVideoToggle")).toBeHidden();
  });
});
