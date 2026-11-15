import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

// UC-43 / AC-19: exercise the real UI with isolated HTTP fixtures, never an application DB.
const employee = { id: 2, ma_nhan_vien: "NV-000002", ho_ten: "Nguyễn Văn An" };
const record = {
  id: 42,
  nhan_vien_id: 2,
  loai_doi_tuong: "yeu_cau_san_xuat",
  doi_tuong_id: 7,
  thao_tac: "kiem_tra",
  created_at: "2026-11-15T02:30:00Z",
  ly_do: "Thiếu linh kiện theo snapshot",
  trang_thai_truoc: "nhap",
  trang_thai_sau: "cho_bo_sung_linh_kien",
  du_lieu_truoc: { trang_thai: "nhap" },
  du_lieu_sau: {
    trang_thai: "cho_bo_sung_linh_kien",
    danh_sach_thieu: [
      {
        mat_hang_id: 8,
        ma_mat_hang: "MH-000008",
        ten_mat_hang: "Khung xe",
        don_vi_tinh: "cai",
        so_luong_can: 12,
        so_luong_con_dung: 2,
        so_luong_thieu: 10,
      },
    ],
  },
};

async function expectReadable(locator) {
  const contrast = await locator.evaluate((element) => {
    const style = getComputedStyle(element);
    const luminance = (color) =>
      color
        .match(/[\d.]+/g)
        .slice(0, 3)
        .map(Number)
        .map((channel) => channel / 255)
        .map((channel) =>
          channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
        )
        .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
    const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => a - b);
    return (values[1] + 0.05) / (values[0] + 0.05);
  });
  expect(contrast).toBeGreaterThanOrEqual(4.5);
}

async function auditApi(page, role, options = {}) {
  return installApi(page, {
    role,
    intercept: async (call) => {
      if (call.path === "nhan_vien" && call.method === "GET")
        return { json: { data: [employee], meta: { page: 1, total_pages: 1 } } };
      if (call.path === "audit/42") {
        if (options.detailGate) await options.detailGate;
        if (options.error)
          return {
            status: options.error,
            json: {
              success: false,
              error: { message: "Không thể đọc lịch sử", code: "test_error" },
            },
          };
        return { json: { success: true, data: options.record || record, meta: {} } };
      }
      if (call.path === "audit") {
        const current = Number(call.params.page || 1);
        return {
          json: {
            success: true,
            data: options.empty ? [] : [{ ...record, id: current === 1 ? 42 : 43 }],
            pagination: {
              page: current,
              page_size: 20,
              total_items: options.empty ? 0 : 21,
              total_pages: options.empty ? 0 : 2,
            },
          },
        };
      }
    },
  });
}

for (const [role, base] of [
  ["quan_tri_vien", "/admin/lich-su"],
  ["quan_ly", "/kho/lich-su"],
]) {
  test(`UC-43 AC-19 ${role}: labels, six AND filters, sort and pagination`, async ({ page }) => {
    const state = await auditApi(page, role);
    await page.goto(base);
    await expect(page.getByRole("cell", { name: "Kiểm tra", exact: true })).toBeVisible();
    await expect(
      page.getByRole("cell", { name: "NV-000002 · Nguyễn Văn An", exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Sắp xếp").locator("option")).toHaveCount(4);
    await page.getByRole("button", { name: "Trang sau", exact: true }).click();
    await expect(page.getByText("Trang 2 / 2", { exact: true })).toBeVisible();
    await page.getByLabel("Loại đối tượng", { exact: true }).selectOption("yeu_cau_san_xuat");
    await page.getByLabel("ID đối tượng", { exact: true }).fill("7");
    await page.getByLabel("Người thực hiện", { exact: true }).selectOption("2");
    await page.getByLabel("Thao tác", { exact: true }).selectOption("kiem_tra");
    await page.getByLabel("Từ ngày", { exact: true }).fill("2026-11-01");
    await page.getByLabel("Đến ngày", { exact: true }).fill("2026-11-15");
    await page.getByLabel("Sắp xếp").selectOption("id");
    await page.getByRole("button", { name: "Lọc", exact: true }).click();
    await expect
      .poll(() => state.calls.filter((call) => call.path === "audit").at(-1)?.params)
      .toEqual({
        page: "1",
        page_size: "20",
        loai_doi_tuong: "yeu_cau_san_xuat",
        doi_tuong_id: "7",
        nhan_vien_id: "2",
        thao_tac: "kiem_tra",
        tu_ngay: "2026-11-01",
        den_ngay: "2026-11-15",
        sort_by: "id",
        sort_order: "asc",
      });
    await expect(page.getByText("Trang 1 / 2", { exact: true })).toBeVisible();
    for (const label of ["Loại đối tượng", "Người thực hiện", "Thao tác"])
      await page.getByLabel(label, { exact: true }).selectOption("");
    for (const label of ["ID đối tượng", "Từ ngày", "Đến ngày"])
      await page.getByLabel(label, { exact: true }).fill("");
    await page.getByRole("button", { name: "Lọc", exact: true }).click();
    await expect
      .poll(() => state.calls.filter((call) => call.path === "audit").at(-1)?.params)
      .toEqual({
        page: "1",
        page_size: "20",
        sort_by: "id",
        sort_order: "asc",
      });
    expect(
      state.calls
        .filter((call) => call.path.startsWith("audit"))
        .every((call) => call.method === "GET"),
    ).toBe(true);
  });

  test(`UC-43 AC-19 ${role}: snapshot detail, keyboard, history and responsive`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await auditApi(page, role);
    await page.goto(base);
    const open = page.getByRole("link", { name: "Mở →", exact: true });
    await expectReadable(
      page
        .getByRole("table", { name: "Danh s\u00e1ch", exact: true })
        .getByRole("columnheader")
        .first(),
    );
    await page.screenshot({ path: `test-results/uc43-${role}-list-desktop.png` });
    await open.click();
    const dialog = page.getByRole("dialog", { name: "Chi tiết lịch sử thao tác" });
    await expect(dialog).toBeVisible();
    await expect(dialog.locator(".badge-amber")).toHaveText("Chờ bổ sung linh kiện");
    await expect(
      dialog.getByRole("row", { name: "MH-000008 · Khung xe cai 12 2 10" }),
    ).toBeVisible();
    await expect(dialog.locator(".audit-json")).toHaveCount(2);
    await expect(dialog.locator(".audit-json").last()).toContainText('"so_luong_thieu": 10');
    await expectReadable(dialog.locator(".audit-json").first());
    await expectReadable(dialog.getByRole("columnheader").first());
    await expect(dialog.getByRole("button", { name: "Đóng", exact: true })).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(dialog.getByRole("button", { name: "Tải lại chi tiết" })).toBeFocused();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Escape");
    await expect(page).toHaveURL(new RegExp(`${base}$`));
    await expect(open).toBeFocused();
    await open.click();
    await page.goBack();
    await expect(dialog).not.toBeVisible();
    await page.goForward();
    await expect(dialog).toBeVisible();
    await page.screenshot({ path: `test-results/uc43-${role}-desktop.png` });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(dialog.getByRole("button", { name: "Đóng", exact: true })).toBeInViewport();
    const bounds = await dialog.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(391);
    await page.screenshot({ path: `test-results/uc43-${role}-mobile.png` });
    await dialog.locator(".table-scroll").evaluate((element) => {
      element.scrollLeft = element.scrollWidth - element.clientWidth;
    });
    expect(
      await dialog.locator(".table-scroll").evaluate((element) => element.scrollLeft),
    ).toBeGreaterThan(0);
    await dialog.locator(".audit-json").last().scrollIntoViewIfNeeded();
    await expect(dialog.locator(".audit-json").last()).toBeInViewport();
    await expect(dialog.getByRole("button", { name: "Đóng", exact: true })).toBeInViewport();
    await expect(dialog.getByRole("button", { name: /^(Sửa|Xóa|Xuất)/ })).toHaveCount(0);
    expect(state.calls.some((call) => call.path === "audit/42" && call.method === "GET")).toBe(
      true,
    );
    expect(
      state.calls
        .filter((call) => call.path.startsWith("audit"))
        .every((call) => call.method === "GET"),
    ).toBe(true);
  });
}

test("UC-43 AC-19 direct detail URL shows loading and null snapshots", async ({ page }) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await auditApi(page, "quan_ly", {
    detailGate: gate,
    record: {
      ...record,
      du_lieu_truoc: null,
      du_lieu_sau: null,
      trang_thai_truoc: null,
      trang_thai_sau: null,
    },
  });
  await page.goto("/kho/lich-su/42");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("status")).toContainText("Đang tải dữ liệu");
  release();
  await expect(dialog.getByText("Không có dữ liệu", { exact: true })).toHaveCount(2);
  await expect(dialog.locator(".info-grid")).toContainText("—");
  await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/lich-su$/);
});

for (const error of [404, 500]) {
  test(`UC-43 AC-19 detail ${error}, empty list and retry`, async ({ page }) => {
    const options = { error, empty: true };
    await auditApi(page, "quan_tri_vien", options);
    await page.goto("/admin/lich-su/42");
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("alert")).toContainText("Không thể đọc lịch sử");
    await expect(page.getByText("Chưa có dữ liệu phù hợp.")).toBeVisible();
    options.error = null;
    await dialog.getByRole("button", { name: "Tải lại", exact: true }).click();
    await expect(dialog.locator(".badge-amber")).toHaveText("Chờ bổ sung linh kiện");
    await expect(dialog.getByRole("alert")).toHaveCount(0);
  });
}

for (const url of ["/admin/lich-su", "/admin/lich-su/42", "/kho/lich-su", "/kho/lich-su/42"]) {
  test(`UC-43 AC-19 NV cannot open ${url}`, async ({ page }) => {
    const state = await auditApi(page, "nhan_vien");
    await page.goto(url);
    await expect(page.getByRole("heading", { name: /không có quyền/i })).toBeVisible();
    expect(state.calls.filter((call) => call.path.startsWith("audit"))).toHaveLength(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
}

test("UC-43 AC-19 admin overview entry and detail breadcrumb", async ({ page }) => {
  await auditApi(page, "quan_tri_vien");
  await page.goto("/admin");
  await page.locator(".admin-activity-card").getByRole("link", { name: "Xem tất cả →" }).click();
  await expect(page).toHaveURL(/\/admin\/lich-su$/);
  await page.getByRole("link", { name: "Mở →", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Đường dẫn trang" })).toContainText(
    "Chi tiết lịch sử",
  );
});
