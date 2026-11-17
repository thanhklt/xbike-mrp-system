import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("assigned employee creates source-only component issue, then confirms send with reviewed ETag", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat = [];
  await page.goto("/nv/yeu-cau/2");
  await page.getByRole("link", { name: "Lập phiếu xuất linh kiện", exact: true }).click();
  const dialog = page.locator("dialog.record-dialog");
  await expect(dialog.getByRole("heading", { name: "Lập phiếu xuất", exact: true })).toBeVisible();
  await expect(dialog.locator("input, select")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/xuat-nvl\/1$/);
  expect(state.calls.find((c) => c.path === "phieu_xuat" && c.method === "POST").body)
    .toEqual({ loai_phieu: "xuat_linh_kien", yeu_cau_san_xuat_id: 2 });
  await expect(dialog.getByText("Phiếu xuất linh kiện", { exact: true })).toBeVisible();
  await expect(dialog.locator("input, select")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Gửi", exact: true }).click();
  const confirmation = page.locator("dialog.confirmation");
  await expect(confirmation).toContainText("8 cái");
  await expect(confirmation).toContainText("YCSX #2");
  await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
  expect(state.calls.filter((c) => c.path === "phieu_xuat/1/gui")).toHaveLength(0);
  await dialog.getByRole("button", { name: "Gửi", exact: true }).click();
  await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmation).toHaveCount(0);
  const send = state.calls.find((c) => c.path === "phieu_xuat/1/gui");
  expect(send.body).toEqual({});
  expect(send.headers["if-match"]).toBe('"v1"');
  await expect(dialog.getByText("Chờ duyệt", { exact: true })).toBeVisible();
  expect(state.calls.filter((c) => c.path === "phieu_xuat" && c.method === "GET")).toEqual([]);
  expect(state.calls.filter((c) => ["PATCH", "DELETE"].includes(c.method))).toEqual([]);
  expect(state.unexpected).toEqual([]);
  await page.screenshot({ path: "test-results/main-issue-sent-desktop.png", fullPage: true });
});

test("rejected issue resends directly and stale ETag keeps confirmation open", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat[0].trang_thai = "tu_choi";
  state.resources.phieu_xuat[0].ly_do_tu_choi = "Kiểm tra lại linh kiện";
  await page.goto("/nv/xuat-nvl/1");
  const dialog = page.locator("dialog.record-dialog");
  await expect(dialog).toContainText("Kiểm tra lại linh kiện");
  await expect(dialog.getByRole("button", { name: /Xóa|Lưu nháp|Chuyển về/ })).toHaveCount(0);
  await dialog.getByRole("button", { name: "Gửi lại", exact: true }).click();
  const quantity = page.locator("dialog.confirmation").getByRole("cell", { name: "8 cái", exact: true });
  await expect(quantity).toBeVisible();
  const quantityBox = await quantity.boundingBox();
  expect(quantityBox.x + quantityBox.width).toBeLessThanOrEqual(375);
  await expect(page.locator("dialog.confirmation th").first()).toHaveCSS("background-color", "rgb(43, 35, 29)");
  await page.screenshot({ path: "test-results/main-issue-resend-mobile.png", fullPage: true });
  state.versions["phieu_xuat/1"] = 2;
  const confirmation = page.locator("dialog.confirmation");
  await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmation.getByRole("alert")).toContainText("Dữ liệu đã thay đổi");
  await expect(confirmation).toBeVisible();
  expect(state.resources.phieu_xuat[0].trang_thai).toBe("tu_choi");
  expect(state.calls.filter((c) => c.path.endsWith("/ve_nhap"))).toHaveLength(0);
  expect(state.calls.filter((c) => c.path === "phieu_xuat/1/gui")).toHaveLength(1);
});

test("product issue requires zero production or approved completion and stays source-only", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat = [];
  state.resources.yeu_cau_san_xuat[1].so_luong_can_san_xuat = 0;
  await page.goto("/nv/yeu-cau/2");
  await expect(page.getByRole("link", { name: "Lập phiếu xuất linh kiện", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Lập phiếu xuất thành phẩm", exact: true }).click();
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/xuat-tp\/1$/);
  const created = state.calls.find((c) => c.path === "phieu_xuat" && c.method === "POST");
  expect(created.body).toEqual({ loai_phieu: "xuat_thanh_pham", yeu_cau_san_xuat_id: 2 });
  expect(state.resources.phieu_xuat[0].chi_tiet[0].so_luong).toBe(20);
});

test("manager sees issue list and approval but cannot create or edit; other employee cannot send", async ({ page }) => {
  const manager = await installApi(page, { role: "quan_ly" });
  await page.goto("/kho/phieu-xuat/1");
  const dialog = page.locator("dialog.record-dialog");
  await expect(page.getByRole("table", { name: "Danh sách phiếu xuất" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Duyệt phiếu xuất", exact: true })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /Gửi|Xóa|Lưu nháp/ })).toHaveCount(0);
  await page.goto("/kho/phieu-xuat/moi");
  await expect(dialog).toContainText("Chỉ nhân viên được giao yêu cầu được lập phiếu xuất.");
  expect(manager.calls.filter((c) => c.path === "phieu_xuat" && c.method === "POST")).toHaveLength(0);
  const employee = await installApi(page, { role: "nhan_vien" });
  employee.resources.yeu_cau_san_xuat[1].nhan_vien_duoc_giao_id = 99;
  await page.goto("/nv/xuat-nvl/1");
  await expect(dialog.getByRole("alert")).toContainText("Không có quyền");
  await expect(dialog.getByRole("button", { name: /Gửi|Duyệt/ })).toHaveCount(0);
});

test("concurrent creation offers existing issue after 409 without forbidden employee list", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  const saved = state.resources.phieu_xuat.slice();
  state.resources.phieu_xuat = [];
  await page.goto("/nv/xuat-nvl/moi?yeu_cau_san_xuat_id=2");
  await expect(page.getByRole("button", { name: "Lưu nháp", exact: true })).toBeEnabled();
  state.resources.phieu_xuat = saved;
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Yêu cầu đã có phiếu xuất loại này");
  await expect(page).toHaveURL(/\/moi\?yeu_cau_san_xuat_id=2$/);
  await page.getByRole("link", { name: `Mở phiếu ${saved[0].ma_phieu_xuat}`, exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/xuat-nvl\/1$/);
  expect(state.resources.phieu_xuat).toHaveLength(2);
  expect(state.calls.filter((c) => c.path === "phieu_xuat" && c.method === "GET")).toHaveLength(0);
});

test("production product issue stays disabled until the linked completion is approved", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat = [];
  state.resources.yeu_cau_san_xuat[1].started_at = "2026-11-05T01:00:00Z";
  state.resources.chung_tu_hoan_thanh_sx.push({ id: 1, yeu_cau_san_xuat_id: 2, trang_thai: "cho_duyet" });
  await page.goto("/nv/xuat-tp/moi?yeu_cau_san_xuat_id=2");
  await expect(page.getByRole("button", { name: "Lưu nháp", exact: true })).toBeDisabled();
  expect(state.calls.filter((c) => c.path === "phieu_xuat" && c.method === "POST")).toHaveLength(0);
  state.resources.chung_tu_hoan_thanh_sx[0].trang_thai = "da_duyet";
  await page.reload();
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/xuat-tp\/1$/);
});

test("existing issue reopens from request after refresh including completed requests", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  const issue = state.resources.phieu_xuat[0];
  state.resources.yeu_cau_san_xuat[1].trang_thai = "hoan_thanh";
  await page.goto("/nv/yeu-cau/2");
  await page.reload();
  await page.getByRole("link", { name: `Mở phiếu ${issue.ma_phieu_xuat}`, exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/xuat-nvl\/1$/);
  expect(state.calls.filter((call) => call.method === "POST")).toHaveLength(0);
  expect(state.calls.filter((call) => call.path === "phieu_xuat" && call.method === "GET")).toHaveLength(0);
});

test("preview loads quantities before save and error retries without creating draft", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat = [];
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  let fail = true;
  await page.route("**/phieu_xuat/xem_truoc/2?*", async (route) => {
    await gate;
    if (fail) return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: { message: "Lỗi tải preview" } }) });
    return route.fallback();
  });
  await page.goto("/nv/xuat-nvl/moi?yeu_cau_san_xuat_id=2");
  const save = page.getByRole("button", { name: "Lưu nháp", exact: true });
  await expect(save).toBeDisabled();
  release();
  await expect(page.getByRole("alert")).toContainText("Lỗi tải preview");
  await expect(save).toBeDisabled();
  fail = false;
  await page.getByRole("button", { name: "Tải lại", exact: true }).click();
  await expect(page.locator("dialog.record-dialog")).toContainText("8 cái");
  await expect(save).toBeEnabled();
  expect(state.resources.phieu_xuat).toHaveLength(0);
  expect(state.calls.filter((call) => call.method === "POST")).toHaveLength(0);
  await page.locator("dialog.record-dialog").getByRole("button", { name: "Đóng", exact: true }).click();
  expect(state.calls.filter((call) => call.method === "POST")).toHaveLength(0);
});
