import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const menus = {
  quan_tri_vien: [
    "/admin",
    "/admin/tai-khoan",
    "/admin/vai-tro",
    "/admin/mat-hang",
    "/admin/nha-cung-cap",
    "/admin/lich-su",
  ],
  quan_ly: [
    "/kho",
    "/kho/mat-hang",
    "/kho/nha-cung-cap",
    "/kho/phieu-nhap",
    "/kho/giao-dich",
    "/kho/bom",
    "/kho/yeu-cau",
    "/kho/nhu-cau-bo-sung",
    "/kho/chung-tu-hoan-thanh",
    "/kho/phieu-xuat",
    "/kho/dieu-chinh",
    "/kho/ticket",
    "/kho/thong-ke",
    "/kho/lich-su",
  ],
  nhan_vien: [
    "/nv",
    "/nv/yeu-cau",
    "/nv/phieu-xuat",
    "/nv/chung-tu-hoan-thanh",
    "/nv/ton-kho",
  ],
};

for (const [role, paths] of Object.entries(menus)) {
  for (const width of [1440, 375]) {
    test(`${role}: sidebar and direct URL permissions at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      const state = await installApi(page, { role });
      await page.goto(paths[0]);
      if (width === 375) await page.getByRole("button", { name: "Mở điều hướng" }).click();
      const sidebar = page.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
      await expect(sidebar).toBeVisible();
      const isDark = role === "quan_tri_vien" || role === "nhan_vien";
      const expectedLinks = isDark ? paths : [...paths, "/ho-so"];
      await expect(sidebar.getByRole("link")).toHaveCount(expectedLinks.length);
      expect(
        await sidebar.getByRole("link").evaluateAll((links) => links.map((link) => link.pathname)),
      ).toEqual(expectedLinks);
      if (isDark) {
        await page.screenshot({ path: `test-results/sidebar-${role}-${width}.png`, fullPage: true });
        if (width === 375 && role === "quan_tri_vien") {
          await sidebar.getByRole("link", { name: "Quản lý tài khoản", exact: true }).click();
          await expect(page).toHaveURL(/\/admin\/tai-khoan$/);
          await expect(page.getByRole("button", { name: "Mở điều hướng" })).toHaveAttribute(
            "aria-expanded",
            "false",
          );
        } else if (width === 375 && role === "nhan_vien") {
          await sidebar.getByRole("link", { name: "Việc được giao", exact: true }).click();
          await expect(page).toHaveURL(/\/nv\/yeu-cau$/);
          await expect(page.getByRole("button", { name: "Mở điều hướng" })).toHaveAttribute(
            "aria-expanded",
            "false",
          );
        }
        await page.locator(".user-menu summary").click();
        await page.locator(".user-dropdown").getByRole("link", { name: /Hồ sơ/ }).click();
        await expect(page).toHaveURL(/\/ho-so$/);
      } else {
        await expect(sidebar.getByRole("button", { name: "Đăng xuất", exact: true })).toBeVisible();
        await page.screenshot({ path: `test-results/sidebar-${role}-${width}.png`, fullPage: true });

        await sidebar.getByRole("link", { name: "Hồ sơ", exact: true }).click();
        await expect(page).toHaveURL(/\/ho-so$/);
        if (width === 375)
          await expect(page.getByRole("button", { name: "Mở điều hướng" })).toHaveAttribute(
            "aria-expanded",
            "false",
          );
      }

      const otherHomes = Object.entries(menus)
        .filter(([otherRole]) => otherRole !== role)
        .map(([, otherPaths]) => otherPaths[0]);
      for (const home of otherHomes) {
        const previousCalls = state.calls.length;
        await page.goto(home);
        await expect(page).toHaveURL(/\/403$/);
        await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
        expect(state.calls.slice(previousCalls).filter((call) => call.path !== "auth/me")).toEqual(
          [],
        );
      }
    });
  }
}

test("refreshing the server role removes the previous sidebar and denies its current page", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_ly" });
  await page.goto("/kho");
  await expect(
    page.locator("#main-navigation").getByRole("link", { name: "Nhà cung cấp" }),
  ).toBeVisible();
  state.role = "nhan_vien";
  await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
  await expect(page).toHaveURL(/\/403$/);
  await page.getByRole("link", { name: "Về trang chủ" }).click();
  await expect(page).toHaveURL(/\/nv$/);
  const sidebar = page.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
  expect(
    await sidebar.getByRole("link").evaluateAll((links) => links.map((link) => link.pathname)),
  ).toEqual(menus.nhan_vien);
});
