import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("request search matches partial product names without case or accents and still finds codes", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.mat_hang.find((item) => item.id === 4).ten_mat_hang = "Xe Đạp Thành Phố";
  await page.goto("/nv/yeu-cau");
  const search = page.getByPlaceholder("Tìm mã yêu cầu hoặc tên thành phẩm…");
  await search.fill("THANH PHO");
  const table = page.getByRole("table", { name: "Danh sách", exact: true });
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(table).toContainText("YCSX-202611-000002");
  await expect(table).toContainText("Xe Đạp Thành Phố");
  await search.fill("khong co san pham nay");
  await expect(table).toContainText("Chưa có dữ liệu phù hợp.");
  await search.fill("ycsx-202611-000002");
  await expect(table).toContainText("Xe Đạp Thành Phố");
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

test("employee cyclic filters preserve collapse, apply valid dates, and leave other roles unchanged", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/yeu-cau");
  const form = page.locator("form.employee-request-filters");
  await expect(page.getByRole("table")).toBeVisible();
  await expect(form.getByLabel("Loại yêu cầu")).toBeHidden();
  await expect(form.getByRole("button", { name: "Hiện thêm" })).toHaveAttribute("aria-expanded", "false");
  await form.getByRole("button", { name: "Hiện thêm" }).click();

  const typeButton = form.locator("#filter-loai_yeu_cau");
  await typeButton.click();
  await expect(typeButton).toContainText("Sản xuất để xuất giao");
  const sortButton = form.locator("#filter-sort");
  await sortButton.click();
  await sortButton.click();
  await sortButton.click();
  await expect(sortButton).toContainText("Mới nhất trước");
  const statusButton = form.locator("#filter-trang_thai");
  await statusButton.focus();
  await page.keyboard.press("Enter");
  await expect(statusButton).toContainText("Đã giao");
  await expect(statusButton).toBeFocused();
  await expect(form.getByRole("listbox")).toHaveCount(0);

  await expect(form.getByLabel("Từ ngày")).toHaveAttribute("placeholder", "dd/mm/yyyy");
  await form.getByLabel("Từ ngày").fill("01/11/2026");
  await form.getByLabel("Đến ngày").fill("30/11/2026");
  await expect.poll(() => state.calls.some((call) => call.path === "yeu_cau_san_xuat"
    && call.params.loai_yeu_cau === "xuat_giao" && call.params.sort === "-created_at"
    && call.params.tu_ngay === "2026-11-01" && call.params.den_ngay === "2026-11-30")).toBe(true);
  await form.getByRole("button", { name: "Ẩn bớt" }).click();
  await expect(form.getByLabel("Loại yêu cầu")).toBeHidden();
  await form.getByRole("button", { name: "Hiện thêm" }).click();
  await expect(typeButton).toContainText("Sản xuất để xuất giao");
  await expect(form.locator("input[name='loai_yeu_cau']")).toHaveValue("xuat_giao");
  await expect(form.getByLabel("Từ ngày")).toHaveValue("01/11/2026");
  const desktopReset = await form.getByRole("button", { name: "Reset tìm kiếm", exact: true }).boundingBox();
  expect(desktopReset.height).toBeLessThanOrEqual(52);
  await page.screenshot({ path: "test-results/employee-request-filters-desktop.png", fullPage: true });

  await page.setViewportSize({ width: 375, height: 812 });
  await expect(page.locator("#main-navigation")).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  const reset = form.getByRole("button", { name: "Reset tìm kiếm", exact: true });
  const resetBounds = await reset.boundingBox();
  expect(resetBounds.x).toBeGreaterThanOrEqual(0);
  expect(resetBounds.x + resetBounds.width).toBeLessThanOrEqual(375);
  await page.screenshot({ path: "test-results/employee-request-filters-mobile.png", fullPage: true });
  await reset.click();
  await expect(typeButton).toContainText("Tất cả");
  await expect(statusButton).toContainText("Tất cả");
  await expect(sortButton).toContainText("Mặc định");
  await expect(form.getByLabel("Từ ngày")).toHaveValue("");
  await expect(form.getByLabel("Đến ngày")).toHaveValue("");
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
  await expect(page.locator("select[name='trang_thai']")).toBeVisible();
  await expect(page.getByRole("button", { name: "Lọc", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reset tìm kiếm", exact: true })).toHaveCount(0);
  await expect(page.locator(".button-dropdown")).toHaveCount(0);

  await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/mat-hang");
  await expect(page.locator("select[name='loai_mat_hang']")).toBeVisible();
  await expect(page.getByRole("button", { name: "Lọc", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reset tìm kiếm", exact: true })).toHaveCount(0);
  await expect(page.locator(".button-dropdown")).toHaveCount(0);
});
