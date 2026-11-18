import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

for (const role of ["nhan_vien", "quan_ly", "quan_tri_vien"]) {
  for (const width of [1440, 375]) {
    test(`${role}: account menu closes outside and keeps keyboard toggle at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await installApi(page, { role });
      await page.goto(role === "nhan_vien" ? "/nv" : role === "quan_ly" ? "/kho" : "/admin");
      const menu = page.locator(".user-menu");
      const summary = menu.locator("summary");
      const dropdown = menu.locator(".user-dropdown");

      await summary.click();
      await expect(dropdown).toBeVisible();
      await dropdown.click({ position: { x: 5, y: 5 } });
      await expect(dropdown).toBeVisible();
      await page.locator("main").click({ position: { x: 5, y: 200 } });
      await expect(dropdown).toBeHidden();

      await summary.focus();
      await page.keyboard.press("Enter");
      await expect(dropdown).toBeVisible();
      await page.keyboard.press("Enter");
      await expect(dropdown).toBeHidden();
      await page.keyboard.press("Enter");
      await dropdown.getByRole("link", { name: "Hồ sơ", exact: true }).click();
      await expect(page).toHaveURL(/\/ho-so$/);
    });
  }
}
