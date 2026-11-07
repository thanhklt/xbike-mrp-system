import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const tabs = [
  ["quan_ly", "/kho/mat-hang"],
  ["quan_ly", "/kho/nha-cung-cap"],
  ["quan_ly", "/kho/bom"],
  ["quan_ly", "/kho/phieu-nhap"],
  ["quan_ly", "/kho/phieu-xuat"],
  ["quan_ly", "/kho/yeu-cau"],
  ["quan_ly", "/kho/lenh-sx"],
  ["quan_ly", "/kho/duyet-hoan-thanh"],
  ["quan_ly", "/kho/dieu-chinh"],
  ["quan_ly", "/kho/ticket"],
  ["nhan_vien", "/nv/lenh-sx"],
  ["nhan_vien", "/nv/yeu-cau"],
  ["nhan_vien", "/nv/xuat-nvl"],
  ["nhan_vien", "/nv/xuat-tp"],
  ["nhan_vien", "/nv/hoan-thanh"],
  ["nhan_vien", "/nv/ton-kho"],
];

test("/admin/tai-khoan: row detail opens the dedicated detail page and Quay lại returns without writing", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan");
  const action = page.locator("table tbody tr").first().getByRole("link", { name: /Chi tiết/ });
  await action.click();
  await expect(page).toHaveURL(/\/admin\/tai-khoan\/1$/);
  await expect(page.getByRole("heading", { name: "Chi tiết tài khoản", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Thông tin tài khoản", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Quay lại", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/tai-khoan$/);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

for (const [role, path] of tabs) {
  test(`${path}: row action opens a modal and closing returns focus without writing`, async ({
    page,
  }) => {
    const state = await installApi(page, { role });
    await page.goto(path);
    const action = page.locator("table tbody tr").first().getByRole("link").last();
    await action.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAccessibleName(/.+/);
    await expect(dialog.locator(".loading")).toHaveCount(0);
    await expect(dialog.getByRole("alert")).toHaveCount(0);
    await expect(page.locator(".record-panel")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    await expect(dialog).toHaveCount(0);
    await expect(action).toBeFocused();
    expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
  });
}

test("record modal supports keyboard navigation, Escape, and browser history", async ({ page }) => {
  await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/lenh-sx");
  const action = page.getByRole("link", { name: "Xem vật tư →" }).first();
  await action.click();
  const dialog = page.getByRole("dialog", { name: "Chi tiết lệnh sản xuất" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Vật tư của lệnh" })).toBeVisible();
  for (let step = 0; step < 12; step += 1) {
    await page.keyboard.press("Tab");
    await expect
      .poll(() => dialog.evaluate((element) => element.contains(document.activeElement)))
      .toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/\/nv\/lenh-sx$/);
  await expect(dialog).toHaveCount(0);
  await expect(action).toBeFocused();
  await action.click();
  await expect(dialog).toBeVisible();
  await page.goBack();
  await expect(dialog).toHaveCount(0);
  await page.goForward();
  await expect(dialog).toBeVisible();
});

test("detail error stays inside the modal and can be closed", async ({ page }) => {
  const state = await installApi(page, {
    intercept: (call) =>
      call.path === "mat_hang/1" && call.method === "GET"
        ? { status: 404, json: { error: { message: "Không tìm thấy mặt hàng" } } }
        : null,
  });
  await page.goto("/kho/mat-hang/1");
  const dialog = page.getByRole("dialog", { name: "Chi tiết mặt hàng" });
  await expect(dialog.getByRole("alert")).toContainText("Không tìm thấy mặt hàng");
  await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/mat-hang$/);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

test("mobile record form scrolls inside the popup and keeps its close control visible", async ({
  page,
}) => {
  await installApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/kho/phieu-nhap/moi");
  const dialog = page.getByRole("dialog", { name: "Tạo phiếu nhập", exact: true });
  await expect(dialog).toBeVisible();
  const bounds = await dialog.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(844);
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).scrollIntoViewIfNeeded();
  await expect(dialog.getByRole("button", { name: "Đóng", exact: true })).toBeInViewport();
  await page.screenshot({ path: "test-results/mobile-record-dialog.png", fullPage: true });
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/\/kho\/phieu-nhap$/);
});
