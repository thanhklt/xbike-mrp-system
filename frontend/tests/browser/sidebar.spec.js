import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const areas = {
  quan_tri_vien: { home: "/admin", detail: "/admin/tai-khoan/1", parent: "/admin/tai-khoan" },
  quan_ly: { home: "/kho", detail: "/kho/phieu-nhap/1", parent: "/kho/phieu-nhap" },
  nhan_vien: { home: "/nv", detail: "/nv/yeu-cau/1", parent: "/nv/yeu-cau" },
};

for (const [role, area] of Object.entries(areas)) {
  test(`${role}: every existing sidebar link navigates and selects its current page`, async ({
    page,
  }) => {
    await installApi(page, { role });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(area.home);
    const panel = page.getByRole("complementary", { name: "Thanh điều hướng" });
    expect(await panel.boundingBox()).toMatchObject({ x: 0, y: 0, height: 900 });
    await expect(
      panel.getByRole("button", { name: /Thu gọn|Mở rộng thanh điều hướng/ }),
    ).toHaveCount(0);
    const sidebar = page.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
    const paths = await sidebar
      .getByRole("link")
      .evaluateAll((links) => links.map((link) => link.pathname));
    for (const path of paths) {
      const link = sidebar.locator(`a[href="${path}"]`);
      await expect(link.locator('svg[aria-hidden="true"]')).toHaveCount(1);
      await link.click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(link).toHaveAttribute("aria-current", "page");
      await expect(sidebar.locator('a[aria-current="page"]')).toHaveCount(1);
    }
    await page.goto(area.detail);
    await expect(sidebar.locator(`a[href="${area.parent}"]`)).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(sidebar.locator(`a[href="${area.home}"]`)).not.toHaveAttribute("aria-current");
    await page.screenshot({ path: `test-results/sidebar-detail-${role}.png`, fullPage: true });
  });
}

test("full-height sidebar keeps hover and keyboard navigation without a collapse button", async ({
  page,
}) => {
  await installApi(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/kho");
  const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
  const header = page.locator(".topbar");
  const headerBefore = await header.innerHTML();
  const headerBox = await header.boundingBox();
  const main = page.locator("#main-content");
  const mainBefore = await main.boundingBox();
  await expect(sidebar).toHaveCSS("width", "264px");
  expect(await sidebar.boundingBox()).toMatchObject({ x: 0, y: 0, height: 900 });
  expect(headerBox.x).toBe(264);
  expect(mainBefore.x).toBe(264);
  await expect(
    sidebar.getByRole("button", { name: /Thu gọn|Mở rộng thanh điều hướng/ }),
  ).toHaveCount(0);
  const inventory = sidebar.getByRole("link", { name: "Mặt hàng & tồn kho", exact: true });
  const restingColor = await inventory.evaluate((link) => getComputedStyle(link).backgroundColor);
  await inventory.hover();
  await expect
    .poll(() => inventory.evaluate((link) => getComputedStyle(link).backgroundColor))
    .not.toBe(restingColor);
  await expect(inventory).toHaveAttribute("title", "Mặt hàng & tồn kho");
  await expect(inventory).toBeVisible();
  await page.keyboard.press("Tab");
  await inventory.focus();
  await expect(inventory).toHaveCSS("outline-style", "solid");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/kho\/mat-hang$/);
  await expect(inventory).toHaveAttribute("aria-current", "page");
  expect(await header.innerHTML()).toBe(headerBefore);
  expect(await header.boundingBox()).toEqual(headerBox);
  expect((await main.boundingBox()).width).toBe(mainBefore.width);
  await page.screenshot({ path: "test-results/sidebar-full-height.png", fullPage: true });
});

for (const width of [768, 375]) {
  test(`mobile/tablet sidebar opens, scrolls and closes after navigation at ${width}px`, async ({
    page,
  }) => {
    await installApi(page);
    await page.setViewportSize({ width, height: 812 });
    await page.goto("/kho");
    const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
    await expect(sidebar).toBeHidden();
    await page.getByRole("button", { name: "Mở điều hướng", exact: true }).click();
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toHaveCSS("width", "280px");
    await expect(
      sidebar.getByRole("button", { name: /Thu gọn|Mở rộng thanh điều hướng/ }),
    ).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    await page.screenshot({ path: `test-results/sidebar-open-${width}.png`, fullPage: true });
    await sidebar.getByRole("link", { name: "Biến động kho", exact: true }).click();
    await expect(page).toHaveURL(/\/kho\/giao-dich$/);
    await expect(sidebar).toBeHidden();
    await expect(page.getByRole("button", { name: "Mở điều hướng", exact: true })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
}

test("responsive sidebar keeps labels and full desktop height with reduced motion", async ({
  page,
}) => {
  await installApi(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/kho");
  const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
  await expect(sidebar).toHaveCSS("width", "240px");
  expect(await sidebar.boundingBox()).toMatchObject({ x: 0, y: 0, height: 900 });
  const inventory = sidebar.getByRole("link", { name: "Mặt hàng & tồn kho", exact: true });
  await expect(inventory).toHaveCSS("transition-duration", "0s");
  await expect(
    sidebar.getByRole("button", { name: /Thu gọn|Mở rộng thanh điều hướng/ }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Mở điều hướng", exact: true }).click();
  await expect(sidebar.getByText("Mặt hàng & tồn kho", { exact: true })).toBeVisible();
  await expect(sidebar).toHaveCSS("width", "280px");
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(sidebar).toHaveCSS("width", "264px");
  expect(await sidebar.boundingBox()).toMatchObject({ x: 0, y: 0, height: 900 });
  await expect(sidebar.getByText("Mặt hàng & tồn kho", { exact: true })).toBeVisible();
});

test("account menu logout keeps confirmation, cancel preserves the session and confirm ends it", async ({
  page,
}) => {
  await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv");
  const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
  await expect(sidebar.getByRole("button", { name: "Đăng xuất", exact: true })).toHaveCount(0);
  await page.locator(".user-menu summary").click();
  await page
    .locator(".user-dropdown")
    .getByRole("button", { name: "Đăng xuất", exact: true })
    .click();
  const confirmation = page.locator("dialog.confirmation");
  await expect(confirmation).toBeVisible();
  await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(confirmation).toHaveCount(0);
  await expect(page).toHaveURL(/\/nv$/);
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBe(
    "browser-test-token",
  );
  await page
    .locator(".user-dropdown")
    .getByRole("button", { name: "Đăng xuất", exact: true })
    .click();
  await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBeNull();
});
