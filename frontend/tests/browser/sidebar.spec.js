import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const areas = {
  quan_tri_vien: { home: "/admin", detail: "/admin/tai-khoan/1", parent: "/admin/tai-khoan" },
  quan_ly: { home: "/kho", detail: "/kho/phieu-nhap/1", parent: "/kho/phieu-nhap" },
  nhan_vien: { home: "/nv", detail: "/nv/lenh-sx/1", parent: "/nv/lenh-sx" },
};

for (const [role, area] of Object.entries(areas)) {
  test(`${role}: every existing sidebar link navigates and selects its current page`, async ({
    page,
  }) => {
    await installApi(page, { role });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(area.home);
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

test("collapse keeps accessible navigation, hover and keyboard controls without changing the header", async ({
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
  const supplier = sidebar.getByRole("link", { name: "Nhà cung cấp", exact: true });
  const restingColor = await supplier.evaluate((link) => getComputedStyle(link).backgroundColor);
  await supplier.hover();
  await expect
    .poll(() => supplier.evaluate((link) => getComputedStyle(link).backgroundColor))
    .not.toBe(restingColor);
  await sidebar.getByRole("button", { name: "Thu gọn thanh điều hướng" }).click();
  await expect(sidebar).toHaveCSS("width", "76px");
  await expect(sidebar.getByRole("button", { name: "Mở rộng thanh điều hướng" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(supplier).toHaveAttribute("title", "Nhà cung cấp");
  await expect(supplier).toBeVisible();
  expect(await header.innerHTML()).toBe(headerBefore);
  expect(await header.boundingBox()).toEqual(headerBox);
  await expect(
    page.getByRole("heading", { name: "Tổng quan kho & sản xuất", exact: true }),
  ).toBeVisible();
  expect((await main.boundingBox()).width).toBeGreaterThan(mainBefore.width);
  await page.screenshot({ path: "test-results/sidebar-collapsed.png", fullPage: true });
  await supplier.click();
  await expect(page).toHaveURL(/\/kho\/nha-cung-cap$/);
  await expect(supplier).toHaveAttribute("aria-current", "page");
  const expand = sidebar.getByRole("button", { name: "Mở rộng thanh điều hướng" });
  await expand.focus();
  await page.keyboard.press("Enter");
  await expect(sidebar).toHaveCSS("width", "264px");
  await expect(sidebar.getByRole("button", { name: "Thu gọn thanh điều hướng" })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
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
    await expect(sidebar.getByRole("button", { name: "Thu gọn thanh điều hướng" })).toBeHidden();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    await page.screenshot({ path: `test-results/sidebar-open-${width}.png`, fullPage: true });
    const profile = sidebar.getByRole("link", { name: "Hồ sơ & đổi mật khẩu", exact: true });
    await profile.click();
    await expect(page).toHaveURL(/\/ho-so$/);
    await expect(sidebar).toBeHidden();
    await expect(page.getByRole("button", { name: "Mở điều hướng", exact: true })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
}

test("desktop collapse does not hide mobile labels and respects reduced motion", async ({
  page,
}) => {
  await installApi(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/kho");
  const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
  await expect(sidebar).toHaveCSS("width", "240px");
  await expect(sidebar).toHaveCSS("transition-duration", "0s");
  await sidebar.getByRole("button", { name: "Thu gọn thanh điều hướng" }).click();
  await expect(sidebar).toHaveCSS("width", "76px");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Mở điều hướng", exact: true }).click();
  await expect(sidebar.getByText("Nhà cung cấp", { exact: true })).toBeVisible();
  await expect(sidebar).toHaveCSS("width", "280px");
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(sidebar).toHaveCSS("width", "76px");
});

test("sidebar logout keeps the existing confirmation and cancel preserves the session", async ({
  page,
}) => {
  await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv");
  const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
  await sidebar.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  const confirmation = page.locator("dialog.confirmation");
  await expect(confirmation).toBeVisible();
  await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(confirmation).toHaveCount(0);
  await expect(page).toHaveURL(/\/nv$/);
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBe(
    "browser-test-token",
  );
});
