import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("ADM-01 overview displays 4 KPI cards in order, role distribution including locked accounts, unwired traffic tabs, and 4-column recent activity", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call, current) => {
      if (call.path === "nhan_vien" && call.method === "GET" && !call.params.vai_tro_id) {
        current.resources.nhan_vien[2].trang_thai = "bi_khoa";
      }
      return null;
    },
  });
  await page.goto("/admin");

  await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();
  const statLabels = await page
    .locator(".admin-stat-card .admin-stat-label")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(statLabels).toEqual([
    "Tổng tài khoản",
    "Tổng vai trò",
    "Tài khoản đang hoạt động",
    "Tài khoản đã vô hiệu hóa",
  ]);
  const statValues = await page
    .locator(".admin-stat-card .admin-stat-value")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(statValues).toEqual(["3", "3", "2", "1"]);

  // Donut includes locked account (total 3, each role 1 (33.3%))
  await expect(page.locator(".admin-donut-center strong")).toHaveText("3");
  await expect(page.locator(".admin-donut-legend")).toContainText("Nhân viên: 1 (33.3%)");
  await expect(page.locator(".admin-donut-legend")).toContainText("Quản lý kho: 1 (33.3%)");
  await expect(page.locator(".admin-donut-legend")).toContainText("Quản trị viên: 1 (33.3%)");

  // Traffic controls are present and make no API calls when clicked
  const beforeCalls = state.calls.length;
  await page.getByRole("button", { name: "7 ngày", exact: true }).click();
  await page.getByRole("button", { name: "30 ngày", exact: true }).click();
  expect(state.calls.length).toBe(beforeCalls);

  // Recent activity 4-column table
  const activityHeaders = await page
    .locator(".admin-activity-card th")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(activityHeaders).toEqual(["Thời gian", "Người thực hiện", "Hành động", "Chi tiết"]);
  await expect(page.locator(".admin-activity-card tbody")).toContainText("Nguyễn Văn An");

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-01-overview-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-01-overview-1672x941.png" });
});

test("ADM-02 account list supports Enter search, immediate filters, page reset, select-all on current page, and only 10 rows per page option", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "quan_tri_vien" });
  state.resources.nhan_vien[0].ngay_sinh = "1990-04-12";
  state.resources.nhan_vien[1].ngay_sinh = "1993-09-05";
  state.resources.nhan_vien[2].ngay_sinh = "1995-01-20";
  for (let index = 4; index <= 14; index += 1) {
    state.resources.nhan_vien.push({
      id: index,
      ten_dang_nhap: `user${index}`,
      ma_nhan_vien: `NV-0000${String(index).padStart(2, "0")}`,
      ho_ten: `Nhân sự ${index}`,
      ma_vai_tro: index % 2 === 0 ? "nhan_vien" : "quan_ly",
      vai_tro_id: index % 2 === 0 ? 3 : 2,
      trang_thai: index === 5 ? "bi_khoa" : "hoat_dong",
      email: `user${index}@example.test`,
      so_dien_thoai: "0901112233",
      ngay_sinh: "1995-08-19",
      ngay_vao_lam: "2025-02-10",
      he_so_luong: "2.35",
    });
  }

  await page.goto("/admin/tai-khoan");
  await expect(page.getByRole("heading", { name: "Quản lý tài khoản", exact: true })).toBeVisible();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(10);

  // Page size selector must offer ONLY [10]
  const pageSizeOptions = await page
    .getByLabel("Số dòng mỗi trang", { exact: true })
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => node.value));
  expect(pageSizeOptions).toEqual(["10"]);

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-02-accounts-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-02-accounts-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Select all selects only current page (10 rows)
  const selectAll = page.getByLabel("Chọn tất cả tài khoản trên trang");
  await selectAll.check();
  await expect(page.locator('.admin-table tbody input[type="checkbox"]:checked')).toHaveCount(10);

  // Navigate to page 2 -> resets selection and shows remaining 4 rows
  await page.getByRole("button", { name: "Trang 2", exact: true }).click();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(4);
  await expect(selectAll).not.toBeChecked();

  // Filter by status applies immediately and resets to page 1
  await page.getByLabel("Trạng thái", { exact: true }).selectOption("bi_khoa");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".admin-table tbody")).toContainText("NV-000005");
  expect(state.calls.at(-1).params).toMatchObject({
    page: "1",
    page_size: "10",
    trang_thai: "bi_khoa",
  });

  // Reset status filter, then search on Enter
  await page.getByLabel("Trạng thái", { exact: true }).selectOption("");
  const searchInput = page.getByLabel("Tìm tài khoản", { exact: true });
  await searchInput.fill("Nguyễn Văn An");
  await searchInput.press("Enter");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".admin-table tbody")).toContainText("NV-000002");
});

test("R2-01 list row lock/unlock fetches snapshot before confirmation, uses reviewed ETag on confirm, fails on 412 without re-fetching ETag, and handles cancel or GET failure safely", async ({
  page,
}) => {
  let failGetId3 = false;
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) => {
      if (failGetId3 && call.path === "nhan_vien/3" && call.method === "GET") {
        return {
          status: 500,
          json: { error: { message: "Không tải được chi tiết nhân viên" } },
        };
      }
      return null;
    },
  });

  await page.goto("/admin/tai-khoan");
  await expect(page.getByRole("heading", { name: "Quản lý tài khoản", exact: true })).toBeVisible();

  // 1. Click row lock on NV-000002 -> GET nhan_vien/2 happens BEFORE confirmation opens
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000002", exact: true }).click();
  const dialog = page.locator("dialog.confirmation");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("NV-000002 · Nguyễn Văn An");
  const getCallsBeforeConfirm = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  );
  expect(getCallsBeforeConfirm).toHaveLength(1);

  // 2. Cancel confirmation -> no DELETE write is sent
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "DELETE"),
  ).toHaveLength(0);

  // 3. Re-open confirmation -> snapshot is v1, then external change bumps version to v2 while dialog is open
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000002", exact: true }).click();
  await expect(dialog).toBeVisible();
  const getCountWhenModalOpened = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  ).length;
  state.versions["nhan_vien/2"] = 2;

  await dialog.getByLabel("Lý do").fill("Nghỉ việc");
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  // Expect 412 error inside dialog, no new GET to refresh ETag, no success toast, single DELETE with If-Match: "v1"
  await expect(dialog.getByRole("alert")).toContainText("Dữ liệu đã thay đổi");
  await expect(page.locator(".toast")).toHaveCount(0);
  const getCountAfterConfirm = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  ).length;
  expect(getCountAfterConfirm).toBe(getCountWhenModalOpened);
  const deleteCalls = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "DELETE",
  );
  expect(deleteCalls).toHaveLength(1);
  expect(deleteCalls[0].headers["if-match"]).toBe('"v1"');

  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);

  // 4. GET failure before confirmation shows error notice and never opens dialog or writes
  failGetId3 = true;
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000003", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText("Không tải được chi tiết nhân viên");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/3" && call.method === "DELETE"),
  ).toHaveLength(0);
});

test("ADM-03 detail view and ADM-05 confirmation popup preserve safety policies, masked password, draft on cancel/close, error handling, and prevent duplicate submits", async ({
  page,
}) => {
  let releasePatch;
  const patchGate = new Promise((resolve) => {
    releasePatch = resolve;
  });
  let failNextPatch = false;
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: async (call) => {
      if (call.path === "nhan_vien/2" && call.method === "PATCH") {
        if (failNextPatch) {
          failNextPatch = false;
          return {
            status: 422,
            json: { error: { message: "Hồ sơ nhân viên không hợp lệ" } },
          };
        }
        await patchGate;
      }
      return null;
    },
  });
  state.resources.nhan_vien[1].ngay_sinh = "1990-04-12";
  state.resources.nhan_vien[1].so_dien_thoai = "0901 234 567";

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/admin/tai-khoan/2");

  // Breadcrumb & 10 fields in order
  await expect(page.getByLabel("Đường dẫn trang")).toContainText("Quản lý tài khoản");
  await expect(page.getByLabel("Đường dẫn trang")).toContainText("Chi tiết tài khoản");
  const labels = await page
    .locator(".admin-detail-row dt span")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(labels).toEqual([
    "Họ tên",
    "Ngày sinh",
    "Số điện thoại",
    "Email",
    "Tên đăng nhập",
    "Mật khẩu",
    "Vai trò",
    "Ngày vào làm",
    "Hệ số lương",
    "Trạng thái",
  ]);
  await expect(page.locator(".admin-detail-row").nth(5).locator("dd")).toHaveText("••••••••");
  await expect(page.locator(".admin-detail-row").nth(7).locator("dd")).toHaveText("01/01/2026");
  await expect(page.locator(".admin-detail-row").nth(8).locator("dd")).toHaveText("1.50");

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-03-detail-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-03-detail-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Open edit mode and trigger ADM-05 confirmation popup
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Họ tên", { exact: true }).fill("Nguyễn Văn An Mới");
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  const dialog = page.locator("dialog.confirmation.confirmation-profile-save");
  await expect(dialog).toBeVisible();

  await page.screenshot({ path: "test-results/adm-05-confirm-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-05-confirm-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Cancel button closes dialog without PATCH and keeps draft
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Họ tên", { exact: true })).toHaveValue("Nguyễn Văn An Mới");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(0);

  // Close (X) button closes dialog without PATCH and keeps draft
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Đóng xác nhận", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Họ tên", { exact: true })).toHaveValue("Nguyễn Văn An Mới");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(0);

  // API error keeps dialog open, shows alert, and never shows success toast
  failNextPatch = true;
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Hồ sơ nhân viên không hợp lệ");
  await expect(page.locator(".toast")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();

  // Confirm and verify duplicate submit protection
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Đang xử lý…" })).toBeDisabled();
  await dialog
    .locator("form")
    .evaluate((form) =>
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
    );
  releasePatch();
  await expect(dialog).toHaveCount(0);
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(2); // 1 failed + 1 succeeded

  // Admin account (id=1) cannot be locked or downgraded
  await page.goto("/admin/tai-khoan/1");
  await expect(page.getByRole("button", { name: "Vô hiệu hóa", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await expect(page.getByRole("button", { name: "Cập nhật vai trò", exact: true })).toBeDisabled();
});

test("ADM-04 roles management displays real API roles, missing description placeholder, only 10 rows per page option, and unwired buttons make no requests", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/vai-tro");

  await expect(page.getByRole("heading", { name: "Quản lý vai trò", exact: true })).toBeVisible();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(3);
  await expect(page.locator(".admin-table tbody")).not.toContainText("Cộng tác viên");
  await expect(page.locator(".admin-table tbody")).not.toContainText("Hỗ trợ kỹ thuật");

  // Page size selector must offer ONLY [10]
  const pageSizeOptions = await page
    .getByLabel("Số dòng mỗi trang", { exact: true })
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => node.value));
  expect(pageSizeOptions).toEqual(["10"]);

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-04-roles-1440x900.png" });
  await page.setViewportSize({ width: 1670, height: 941 });
  await page.screenshot({ path: "test-results/adm-04-roles-1670x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Delete buttons for the 3 system roles are disabled as in design
  await expect(page.getByRole("button", { name: "Xóa Quản trị viên" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Xóa Quản lý kho" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Xóa Nhân viên" })).toBeDisabled();

  // Unwired buttons (+ Tạo vai trò, Sửa) remain enabled and make no API calls or fake toasts
  const beforeCalls = state.calls.length;
  await page.getByRole("button", { name: "Tạo vai trò", exact: true }).click();
  await page.getByRole("button", { name: "Sửa Quản trị viên", exact: true }).click();
  expect(state.calls.length).toBe(beforeCalls);
  await expect(page.locator(".toast")).toHaveCount(0);
  await expect(page.locator("dialog[open]")).toHaveCount(0);

  // Client-side search on Enter
  const search = page.getByLabel("Tìm vai trò", { exact: true });
  await search.fill("Quản lý kho");
  await search.press("Enter");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
});
