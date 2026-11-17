import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("request search matches partial product names without case or accents and still finds codes", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.mat_hang.find((item) => item.id === 4).ten_mat_hang = "Xe Đạp Thành Phố";
  await page.goto("/nv/yeu-cau");
  const search = page.getByPlaceholder("Tìm mã yêu cầu hoặc tên thành phẩm…");
  await search.fill("THANH PHO");
  await search.press("Enter");
  const table = page.getByRole("table", { name: "Danh sách", exact: true });
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(table).toContainText("YCSX-202611-000002");
  await expect(table).toContainText("Xe Đạp Thành Phố");
  await search.fill("khong co san pham nay");
  await search.press("Enter");
  await expect(table).toContainText("Chưa có dữ liệu phù hợp.");
  await search.fill("ycsx-202611-000002");
  await search.press("Enter");
  await expect(table).toContainText("Xe Đạp Thành Phố");
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

test("employee request filters collapse without losing values and submit supported parameters", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/yeu-cau");
  const form = page.locator("form.employee-request-filters");
  await expect(form).toBeVisible();
  await page.getByRole("table").waitFor();
  await expect(form.getByLabel("Loại yêu cầu")).toBeHidden();
  await expect(form.getByRole("button", { name: "Hiện thêm" })).toHaveAttribute("aria-expanded", "false");
  await form.getByRole("button", { name: "Hiện thêm" }).click();
  await page.screenshot({ path: "test-results/employee-request-filters-desktop.png", fullPage: true });
  await form.getByLabel("Loại yêu cầu").selectOption("xuat_giao");
  await form.getByLabel("Sắp xếp").selectOption("-created_at");
  await form.getByLabel("Từ ngày").fill("2026-11-01");
  await form.getByLabel("Đến ngày").fill("2026-11-30");
  const toggle = form.getByRole("button", { name: "Ẩn bớt" });
  await toggle.click();
  await expect(form.getByLabel("Loại yêu cầu")).toBeHidden();
  await expect(form.getByRole("button", { name: "Hiện thêm" })).toHaveAttribute("aria-expanded", "false");
  await form.getByRole("button", { name: "Lọc", exact: true }).click();
  await expect.poll(() => state.calls.some((call) => call.path === "yeu_cau_san_xuat"
    && call.params.loai_yeu_cau === "xuat_giao" && call.params.sort === "-created_at"
    && call.params.tu_ngay === "2026-11-01" && call.params.den_ngay === "2026-11-30")).toBe(true);
  await form.getByRole("button", { name: "Hiện thêm" }).click();
  await expect(form.getByLabel("Loại yêu cầu")).toHaveValue("xuat_giao");
  await expect(form.getByLabel("Từ ngày")).toHaveValue("2026-11-01");
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(page.locator("#main-navigation")).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  await page.screenshot({ path: "test-results/employee-request-filters-mobile.png", fullPage: true, animations: "disabled" });
  expect(state.unexpected).toEqual([]);

  await page.goto("/nv");
  await expect(page.locator(".employee-overview")).toBeAttached();
  await page.goto("/nv/yeu-cau");
  await expect(form.getByLabel("Loại yêu cầu")).toBeHidden();
  await expect(form.getByRole("button", { name: "Hiện thêm" })).toHaveAttribute("aria-expanded", "false");

  await installApi(page, { role: "quan_ly" });
  await page.goto("/kho/yeu-cau");
  await expect(page.locator("form.filters")).toBeVisible();
  await expect(page.locator(".employee-request-filters")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Ẩn bớt" })).toHaveCount(0);
});
